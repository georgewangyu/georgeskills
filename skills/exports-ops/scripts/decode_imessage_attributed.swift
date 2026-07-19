#!/usr/bin/env swift
import Foundation

// Read one base64-encoded NSArchiver payload per line and emit the decoded
// string as base64. A leading exclamation point marks a decode failure. The
// line protocol keeps private message text out of process arguments and logs.
while let line = readLine() {
    guard let data = Data(base64Encoded: line) else {
        print("!invalid-base64")
        fflush(stdout)
        continue
    }

    let object = NSUnarchiver.unarchiveObject(with: data)
    let value: String
    if let attributed = object as? NSAttributedString {
        value = attributed.string
    } else if let string = object as? String {
        value = string
    } else {
        print("!unsupported-object")
        fflush(stdout)
        continue
    }
    print(Data(value.utf8).base64EncodedString())
    fflush(stdout)
}
