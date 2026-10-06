plugins {
    id("com.android.application")
}

android {
    namespace = "org.pooltool.android"
    compileSdk = 37

    defaultConfig {
        applicationId = "org.pooltool.android"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
