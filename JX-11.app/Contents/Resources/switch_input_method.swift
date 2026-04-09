#!/usr/bin/env swift
import Carbon

let sources = TISCreateInputSourceList(nil, false).takeRetainedValue() as! [TISInputSource]
let keyboards = sources.filter { src in
    guard let cat = Unmanaged<CFString>.fromOpaque(TISGetInputSourceProperty(src, kTISPropertyInputSourceCategory)).takeUnretainedValue() as String?,
          let sel = Unmanaged<CFBoolean>.fromOpaque(TISGetInputSourceProperty(src, kTISPropertyInputSourceIsSelectCapable)).takeUnretainedValue() as? Bool else { return false }
    return cat == "TISCategoryKeyboardInputSource" && sel
}

guard !keyboards.isEmpty else { exit(1) }

let currentIdx = keyboards.firstIndex(where: { src in
    guard let sel = Unmanaged<CFBoolean>.fromOpaque(TISGetInputSourceProperty(src, kTISPropertyInputSourceIsSelected)).takeUnretainedValue() as? Bool else { return false }
    return sel == true
}) ?? 0

let nextIdx = (currentIdx + 1) % keyboards.count
TISSelectInputSource(keyboards[nextIdx])
