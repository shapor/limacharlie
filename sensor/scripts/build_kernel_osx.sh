#! /bin/sh

xcodebuild -project ./sensor/executables/hbs_kernel_acquisition/osx/hbs_kernel_acquisition.xcodeproj/

mkdir -p ./sensor/bin/macosx/kernel
cp -R ./sensor/executables/hbs_kernel_acquisition/osx/build/Release/hbs_kernel_acquisition.kext ./sensor/bin/macosx/kernel/hbs_kernel_acquisition.kext

