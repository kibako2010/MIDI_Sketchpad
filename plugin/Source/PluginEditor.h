#pragma once

#include <juce_gui_extra/juce_gui_extra.h>
#include "PluginProcessor.h"

class MidiSketchpadAudioProcessorEditor : public juce::AudioProcessorEditor,
                                          private juce::Button::Listener
{
public:
    explicit MidiSketchpadAudioProcessorEditor(MidiSketchpadAudioProcessor&);
    ~MidiSketchpadAudioProcessorEditor() override;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    void buttonClicked(juce::Button* button) override;

    MidiSketchpadAudioProcessor& processorRef;

    juce::Label title;
    juce::TextEditor chordsEditor;
    juce::TextEditor promptEditor;
    juce::TextButton generateButton { "マスター生成" };
    juce::Label statusLabel;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MidiSketchpadAudioProcessorEditor)
};
