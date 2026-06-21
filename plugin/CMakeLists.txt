cmake_minimum_required(VERSION 3.22)
project(MIDISketchpadPlugin VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(JUCE CONFIG REQUIRED)

juce_add_plugin(MIDISketchpad
    COMPANY_NAME "Kibako"
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD TRUE
    PLUGIN_MANUFACTURER_CODE Kiba
    PLUGIN_CODE Msk0
    FORMATS Standalone VST3
    PRODUCT_NAME "MIDI Sketchpad"
)

target_sources(MIDISketchpad PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp
    Source/BackendBridge.cpp
    Source/PluginSettings.cpp
    Source/JsonUtil.cpp
)

target_include_directories(MIDISketchpad PRIVATE Source)

target_link_libraries(MIDISketchpad
    PRIVATE
        juce::juce_audio_utils
        juce::juce_gui_extra
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags
)
