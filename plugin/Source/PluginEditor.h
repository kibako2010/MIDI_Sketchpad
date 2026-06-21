#pragma once

#include <array>
#include <juce_gui_extra/juce_gui_extra.h>
#include "PluginProcessor.h"

class MidiSketchpadAudioProcessorEditor : public juce::AudioProcessorEditor,
                                          private juce::Button::Listener,
                                          private juce::Slider::Listener,
                                          private juce::TextEditor::Listener
{
public:
    explicit MidiSketchpadAudioProcessorEditor(MidiSketchpadAudioProcessor&);
    ~MidiSketchpadAudioProcessorEditor() override;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    struct TrackRow
    {
        juce::Label nameLabel;
        juce::ToggleButton enableToggle;
        juce::Slider gainSlider;
        juce::Label gainLabel;
        juce::ComboBox midiOutBox;
        juce::TextButton generateButton { "Generate ✨" };
    };

    struct LayoutRects
    {
        juce::Rectangle<int> header;
        juce::Rectangle<int> sectionRow;
        juce::Rectangle<int> chordsPanel;
        juce::Rectangle<int> stylePanel;
        juce::Rectangle<int> tracksPanel;
        juce::Rectangle<int> bottomRow;
        juce::Rectangle<int> humanizePanel;
        juce::Rectangle<int> masterButton;
        juce::Rectangle<int> exportPanel;
        juce::Rectangle<int> settingsButton;
        juce::Rectangle<int> footer;
    };

    LayoutRects calculateLayout() const;
    void drawPanel(juce::Graphics& g, juce::Rectangle<int> area, juce::StringRef title, juce::Colour accent) const;

    void stylePrimaryButton(juce::TextButton& button);
    void styleOutlineButton(juce::TextButton& button);
    void styleSmallButton(juce::TextButton& button);
    void styleEditor(juce::TextEditor& editor, bool multiLine = false);

    void updatePromptCounter();
    void syncUiState();

    void buttonClicked(juce::Button* button) override;
    void sliderValueChanged(juce::Slider* slider) override;
    void textEditorTextChanged(juce::TextEditor& editor) override;

    MidiSketchpadAudioProcessor& processorRef;

    juce::Label titleLabel;
    juce::Label subtitleLabel;
    juce::Label lmStudioLabel;
    juce::Label lmStatusLabel;
    juce::TextButton disconnectButton { "Disconnect" };

    juce::Label chordCaptionLabel;
    juce::TextEditor chordsEditor;
    juce::Label chordHelpLabel;
    juce::TextButton importMidiButton { "Import MIDI File..." };
    juce::TextButton generateChordsButton { "Generate Chords ✨" };

    juce::Label promptCaptionLabel;
    juce::TextEditor promptEditor;
    juce::Label promptCountLabel;
    juce::Label bpmLabel;
    juce::TextButton bpmMinusButton { "-" };
    juce::Label bpmValueLabel;
    juce::TextButton bpmPlusButton { "+" };
    juce::Label timeSigLabel;
    juce::ComboBox timeSigNumBox;
    juce::ComboBox timeSigDenBox;
    juce::Label slashLabel;
    juce::Label seedLabel;
    juce::TextEditor seedEditor;
    juce::TextButton randomizeButton { "Randomize" };
    juce::Label seedNoticeLabel;

    juce::Label tracksHeaderEnableLabel;
    juce::Label tracksHeaderOutputLabel;
    juce::Label tracksHeaderGenerateLabel;
    std::array<TrackRow, 7> trackRows;

    juce::Label humanizeTitleLabel;
    juce::Label humanizeHintLabel;
    juce::Slider humanizeSlider;
    juce::Label humanizeValueLabel;

    juce::TextButton masterGenerateButton { "⚡  MASTER GENERATE" };
    juce::TextButton exportButton { "Export All MIDI..." };
    juce::Label exportHintLabel;
    juce::TextButton settingsButton { "⚙" };

    juce::Label footerLabel;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MidiSketchpadAudioProcessorEditor)
};
