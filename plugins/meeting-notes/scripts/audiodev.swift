// audiodev — CoreAudio 집합/다중출력 장치 생성·삭제·조회 CLI
// 회의 녹음 파이프라인용. Audio MIDI 설정 GUI 없이 스크립트로 장치를 다룬다.
//
// 빌드: swiftc -O -o audiodev audiodev.swift
// 사용: audiodev list
//       audiodev create --name "이름" --uid "고유id" --sub UID1 --sub UID2 --master UID1 [--stacked] [--drift UID2]
//       audiodev destroy --uid "고유id"

import Foundation
import CoreAudio

// MARK: - 장치 조회

struct Device {
    let id: AudioDeviceID
    let name: String
    let uid: String
    let inChannels: Int
    let outChannels: Int
}

func systemDeviceIDs() -> [AudioDeviceID] {
    var addr = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDevices,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var size: UInt32 = 0
    guard AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size) == noErr
    else { return [] }
    var ids = [AudioDeviceID](repeating: 0, count: Int(size) / MemoryLayout<AudioDeviceID>.size)
    guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &ids) == noErr
    else { return [] }
    return ids
}

func stringProperty(_ id: AudioDeviceID, _ selector: AudioObjectPropertySelector) -> String? {
    var addr = AudioObjectPropertyAddress(
        mSelector: selector,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var size = UInt32(MemoryLayout<CFString?>.size)
    var value: CFString? = nil
    let status = withUnsafeMutablePointer(to: &value) {
        AudioObjectGetPropertyData(id, &addr, 0, nil, &size, $0)
    }
    guard status == noErr, let v = value else { return nil }
    return v as String
}

func channelCount(_ id: AudioDeviceID, scope: AudioObjectPropertyScope) -> Int {
    var addr = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyStreamConfiguration,
        mScope: scope,
        mElement: kAudioObjectPropertyElementMain)
    var size: UInt32 = 0
    guard AudioObjectGetPropertyDataSize(id, &addr, 0, nil, &size) == noErr, size > 0 else { return 0 }
    let buf = UnsafeMutableRawPointer.allocate(byteCount: Int(size), alignment: MemoryLayout<AudioBufferList>.alignment)
    defer { buf.deallocate() }
    guard AudioObjectGetPropertyData(id, &addr, 0, nil, &size, buf) == noErr else { return 0 }
    let ablPtr = UnsafeMutableAudioBufferListPointer(buf.assumingMemoryBound(to: AudioBufferList.self))
    return ablPtr.reduce(0) { $0 + Int($1.mNumberChannels) }
}

func allDevices() -> [Device] {
    systemDeviceIDs().compactMap { id in
        guard let name = stringProperty(id, kAudioObjectPropertyName),
              let uid = stringProperty(id, kAudioDevicePropertyDeviceUID) else { return nil }
        return Device(id: id,
                      name: name,
                      uid: uid,
                      inChannels: channelCount(id, scope: kAudioObjectPropertyScopeInput),
                      outChannels: channelCount(id, scope: kAudioObjectPropertyScopeOutput))
    }
}

// MARK: - 생성·삭제

// CoreAudio 딕셔너리 키는 SDK 버전에 따라 상수명이 바뀌어(master→main) 문자열 리터럴로 고정한다.
func createAggregate(name: String, uid: String, subUIDs: [String], masterUID: String,
                     stacked: Bool, driftUIDs: Set<String>) -> Int32 {
    let subs: [[String: Any]] = subUIDs.map { s in
        var d: [String: Any] = ["uid": s]
        if driftUIDs.contains(s) { d["drift"] = 1 }
        return d
    }
    let desc: [String: Any] = [
        "name": name,
        "uid": uid,
        "subdevices": subs,
        "master": masterUID,
        "private": 0,
        "stacked": stacked ? 1 : 0,
    ]
    var devID = AudioObjectID(0)
    return AudioHardwareCreateAggregateDevice(desc as CFDictionary, &devID)
}

func destroyAggregate(uid: String) -> Int32 {
    guard let dev = allDevices().first(where: { $0.uid == uid }) else { return -1 }
    return AudioHardwareDestroyAggregateDevice(dev.id)
}

// MARK: - 음소거·볼륨
//
// 가상 장치(BlackHole)가 음소거되어 있으면 들어가는 샘플이 그대로 0이 되어
// "녹음은 되는데 무음"인 상태가 된다. 녹음 전에 반드시 해제해야 한다.

func isMuted(_ id: AudioDeviceID) -> Bool? {
    var addr = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyMute,
        mScope: kAudioObjectPropertyScopeOutput,
        mElement: kAudioObjectPropertyElementMain)
    guard AudioObjectHasProperty(id, &addr) else { return nil }
    var value: UInt32 = 0
    var size = UInt32(MemoryLayout<UInt32>.size)
    guard AudioObjectGetPropertyData(id, &addr, 0, nil, &size, &value) == noErr else { return nil }
    return value != 0
}

@discardableResult
func setMute(_ id: AudioDeviceID, _ mute: Bool) -> Bool {
    var addr = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyMute,
        mScope: kAudioObjectPropertyScopeOutput,
        mElement: kAudioObjectPropertyElementMain)
    var settable: DarwinBoolean = false
    guard AudioObjectHasProperty(id, &addr),
          AudioObjectIsPropertySettable(id, &addr, &settable) == noErr, settable.boolValue else { return false }
    var value: UInt32 = mute ? 1 : 0
    return AudioObjectSetPropertyData(id, &addr, 0, nil, UInt32(MemoryLayout<UInt32>.size), &value) == noErr
}

/// 마스터 엘리먼트와 개별 채널을 모두 시도한다 (장치마다 지원 범위가 다르다).
@discardableResult
func setVolume(_ id: AudioDeviceID, _ value: Float32) -> Bool {
    var applied = false
    for element in [kAudioObjectPropertyElementMain, 1, 2] {
        var addr = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyVolumeScalar,
            mScope: kAudioObjectPropertyScopeOutput,
            mElement: AudioObjectPropertyElement(element))
        guard AudioObjectHasProperty(id, &addr) else { continue }
        var settable: DarwinBoolean = false
        guard AudioObjectIsPropertySettable(id, &addr, &settable) == noErr, settable.boolValue else { continue }
        var v = value
        if AudioObjectSetPropertyData(id, &addr, 0, nil, UInt32(MemoryLayout<Float32>.size), &v) == noErr {
            applied = true
        }
    }
    return applied
}

// MARK: - CLI

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(1)
}

let args = Array(CommandLine.arguments.dropFirst())
guard let command = args.first else {
    fail("usage: audiodev list | create ... | destroy --uid UID")
}

func option(_ flag: String) -> String? {
    guard let i = args.firstIndex(of: flag), i + 1 < args.count else { return nil }
    return args[i + 1]
}

func options(_ flag: String) -> [String] {
    var out: [String] = []
    for (i, a) in args.enumerated() where a == flag && i + 1 < args.count {
        out.append(args[i + 1])
    }
    return out
}

switch command {
case "list":
    // 탭 구분: name \t uid \t in_ch \t out_ch
    for d in allDevices() {
        print("\(d.name)\t\(d.uid)\t\(d.inChannels)\t\(d.outChannels)")
    }

case "create":
    guard let name = option("--name"), let uid = option("--uid") else {
        fail("create: --name 과 --uid 는 필수")
    }
    let subs = options("--sub")
    guard !subs.isEmpty else { fail("create: --sub 를 하나 이상 지정") }
    let master = option("--master") ?? subs[0]
    let status = createAggregate(name: name, uid: uid, subUIDs: subs, masterUID: master,
                                 stacked: args.contains("--stacked"),
                                 driftUIDs: Set(options("--drift")))
    if status != noErr { fail("create 실패: OSStatus \(status)") }
    print(uid)

case "destroy":
    guard let uid = option("--uid") else { fail("destroy: --uid 필수") }
    let status = destroyAggregate(uid: uid)
    if status != noErr { fail("destroy 실패: OSStatus \(status)") }

case "ensure-audible":
    // 음소거 해제 + 볼륨 최대. 녹음 직전에 호출해 "무음 녹음"을 예방한다.
    guard let uid = option("--uid") else { fail("ensure-audible: --uid 필수") }
    guard let dev = allDevices().first(where: { $0.uid == uid }) else { fail("장치를 찾을 수 없음: \(uid)") }
    let was = isMuted(dev.id)
    setMute(dev.id, false)
    setVolume(dev.id, 1.0)
    print(was == true ? "unmuted" : "ok")

default:
    fail("알 수 없는 명령: \(command)")
}
