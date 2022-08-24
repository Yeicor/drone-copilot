# Build/deploy instructions

## MacOS, Windows and Linux

```
pip install -r requirements.txt
python3 main.py
```

## Android

Currently, you can only build for Android using buildozer on Linux.
You need to install buildozer and other build dependencies first:

```
pip install buildozer cython
```

Then you can build (and optionally run) the APK:

```
buildozer android debug [deploy run]
```

## iOS (not tested)

Remember that you will need an Apple developer account to be able to install your app on a real iPhone.

Install Cocoapods if you haven't already:

```
brew install cocoapods
```

Build your app and install the Tensorflow Lite pod:

```
buildozer ios debug

cd .buildozer/ios/platform/kivy-ios/myapp-ios/

cp YourApp/Podfile .

pod install

open -a Xcode myapp.xcworkspace
```

From now on you should open the workspace as opposed to the project. You will almost certainly have to make some changes
to the myapp target in Xcode as indicated by `buildozer ios debug` and `pod install`. Every time you build you will need
to run `buildozer ios debug` and then build and deploy from Xcode.
