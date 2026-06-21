#include "PluginEditor.h"

#include <cmath>

namespace
{
constexpr auto kPanelBg = juce::Colour(0xff111827);
constexpr auto kPanelBorder = juce::Colour(0xff1f2937);
constexpr auto kAccent = juce::Colour(0xff22d3ee);
constexpr auto kAccentSoft = juce::Colour(0xff0ea5e9);
constexpr auto kTextMain = juce::Colour(0xffe2e8f0);
constexpr auto kTextMuted = juce::Colour(0xff94a3b8);
constexpr auto kPositive = juce::Colour(0xff10b981);

const std::array<juce::String, 7> kTrackNames = {
    "1. Drums / Bodhrán", "2. Bass", "3. Guitar", "4. Fiddle", "5. Whistle", "6. Pad", "7. Chord Track"
};
}

MidiSketchpadAudioProcessorEditor::MidiSketchpadAudioProcessorEditor(MidiSketchpadAudioProcessor& p)
    : AudioProcessorEditor(&p), processorRef(p)
{
    setOpaque(true);
    setSize(1120, 700);

    titleLabel.setText("MIDI Sketchpad v0.3", juce::dontSendNotification);
    titleLabel.setColour(juce::Label::textColourId, kTextMain);
    titleLabel.setFont(juce::Font(40.0f, juce::Font::bold));
    addAndMakeVisible(titleLabel);

    subtitleLabel.setText("AI-POWERED GENRE-BASED MIDI ACCOMPANIMENT GENERATOR", juce::dontSendNotification);
    subtitleLabel.setColour(juce::Label::textColourId, kTextMuted);
    subtitleLabel.setFont(juce::Font(12.0f));
    addAndMakeVisible(subtitleLabel);

    lmStudioLabel.setText("LM Studio", juce::dontSendNotification);
    lmStudioLabel.setColour(juce::Label::textColourId, kTextMain);
    lmStudioLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(lmStudioLabel);

    lmStatusLabel.setText("● CONNECTED", juce::dontSendNotification);
    lmStatusLabel.setColour(juce::Label::textColourId, kPositive);
    lmStatusLabel.setJustificationType(juce::Justification::centredLeft);
    addAndMakeVisible(lmStatusLabel);

    styleSmallButton(disconnectButton);
    disconnectButton.addListener(this);
    addAndMakeVisible(disconnectButton);

    chordCaptionLabel.setText("Enter your chord progression", juce::dontSendNotification);
    chordCaptionLabel.setColour(juce::Label::textColourId, kTextMain);
    addAndMakeVisible(chordCaptionLabel);

    styleEditor(chordsEditor, true);
    chordsEditor.setText("| Am | F | C | G |\n| Am | F | C | G |\n| F  | G | Am | E |\n| Am | F | C | G ||", false);
    addAndMakeVisible(chordsEditor);

    chordHelpLabel.setText("Format: Use | to separate bars, chords per bar.", juce::dontSendNotification);
    chordHelpLabel.setColour(juce::Label::textColourId, kTextMuted);
    addAndMakeVisible(chordHelpLabel);

    styleSmallButton(importMidiButton);
    importMidiButton.addListener(this);
    addAndMakeVisible(importMidiButton);

    styleOutlineButton(generateChordsButton);
    generateChordsButton.addListener(this);
    addAndMakeVisible(generateChordsButton);

    promptCaptionLabel.setText("Describe your music style", juce::dontSendNotification);
    promptCaptionLabel.setColour(juce::Label::textColourId, kTextMain);
    addAndMakeVisible(promptCaptionLabel);

    styleEditor(promptEditor, true);
    promptEditor.setText("6/8 Anime Irish, energetic, bright", false);
    promptEditor.addListener(this);
    addAndMakeVisible(promptEditor);

    promptCountLabel.setColour(juce::Label::textColourId, kTextMuted);
    promptCountLabel.setJustificationType(juce::Justification::centredRight);
    addAndMakeVisible(promptCountLabel);

    bpmLabel.setText("BPM", juce::dontSendNotification);
    bpmLabel.setColour(juce::Label::textColourId, kTextMain);
    addAndMakeVisible(bpmLabel);

    styleSmallButton(bpmMinusButton);
    styleSmallButton(bpmPlusButton);
    bpmMinusButton.addListener(this);
    bpmPlusButton.addListener(this);
    addAndMakeVisible(bpmMinusButton);
    addAndMakeVisible(bpmPlusButton);

    bpmValueLabel.setText("120", juce::dontSendNotification);
    bpmValueLabel.setJustificationType(juce::Justification::centred);
    bpmValueLabel.setColour(juce::Label::backgroundColourId, juce::Colour(0xff0f172a));
    bpmValueLabel.setColour(juce::Label::outlineColourId, kPanelBorder);
    bpmValueLabel.setColour(juce::Label::textColourId, kTextMain);
    addAndMakeVisible(bpmValueLabel);

    timeSigLabel.setText("Time Signature", juce::dontSendNotification);
    timeSigLabel.setColour(juce::Label::textColourId, kTextMain);
    addAndMakeVisible(timeSigLabel);

    timeSigNumBox.addItem("3", 3);
    timeSigNumBox.addItem("4", 4);
    timeSigNumBox.addItem("6", 6);
    timeSigNumBox.addItem("7", 7);
    timeSigNumBox.setSelectedId(6);
    timeSigNumBox.setColour(juce::ComboBox::backgroundColourId, juce::Colour(0xff0f172a));
    timeSigNumBox.setColour(juce::ComboBox::outlineColourId, kPanelBorder);
    timeSigNumBox.setColour(juce::ComboBox::textColourId, kTextMain);
    addAndMakeVisible(timeSigNumBox);

    timeSigDenBox.addItem("4", 4);
    timeSigDenBox.addItem("8", 8);
    timeSigDenBox.addItem("16", 16);
    timeSigDenBox.setSelectedId(8);
    timeSigDenBox.setColour(juce::ComboBox::backgroundColourId, juce::Colour(0xff0f172a));
    timeSigDenBox.setColour(juce::ComboBox::outlineColourId, kPanelBorder);
    timeSigDenBox.setColour(juce::ComboBox::textColourId, kTextMain);
    addAndMakeVisible(timeSigDenBox);

    slashLabel.setText("/", juce::dontSendNotification);
    slashLabel.setColour(juce::Label::textColourId, kTextMuted);
    slashLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(slashLabel);

    seedLabel.setText("Seed (for reproducibility)", juce::dontSendNotification);
    seedLabel.setColour(juce::Label::textColourId, kTextMain);
    addAndMakeVisible(seedLabel);

    styleEditor(seedEditor);
    seedEditor.setText("12345", false);
    seedEditor.addListener(this);
    addAndMakeVisible(seedEditor);

    styleSmallButton(randomizeButton);
    randomizeButton.addListener(this);
    addAndMakeVisible(randomizeButton);

    seedNoticeLabel.setText("ⓘ  Same seed + settings = same MIDI output", juce::dontSendNotification);
    seedNoticeLabel.setColour(juce::Label::textColourId, juce::Colour(0xffbfdbfe));
    seedNoticeLabel.setJustificationType(juce::Justification::centredLeft);
    addAndMakeVisible(seedNoticeLabel);

    tracksHeaderEnableLabel.setText("Enable", juce::dontSendNotification);
    tracksHeaderEnableLabel.setColour(juce::Label::textColourId, kTextMuted);
    addAndMakeVisible(tracksHeaderEnableLabel);

    tracksHeaderOutputLabel.setText("MIDI Output", juce::dontSendNotification);
    tracksHeaderOutputLabel.setColour(juce::Label::textColourId, kTextMuted);
    addAndMakeVisible(tracksHeaderOutputLabel);

    tracksHeaderGenerateLabel.setText("Generate", juce::dontSendNotification);
    tracksHeaderGenerateLabel.setColour(juce::Label::textColourId, kTextMuted);
    addAndMakeVisible(tracksHeaderGenerateLabel);

    for (size_t i = 0; i < trackRows.size(); ++i)
    {
        auto& row = trackRows[i];

        row.nameLabel.setText(kTrackNames[i], juce::dontSendNotification);
        row.nameLabel.setColour(juce::Label::textColourId, kTextMain);
        addAndMakeVisible(row.nameLabel);

        row.enableToggle.setToggleState(true, juce::dontSendNotification);
        row.enableToggle.setClickingTogglesState(true);
        row.enableToggle.setColour(juce::ToggleButton::tickColourId, kAccent);
        row.enableToggle.setButtonText({});
        addAndMakeVisible(row.enableToggle);

        row.gainSlider.setSliderStyle(juce::Slider::LinearHorizontal);
        row.gainSlider.setRange(-12.0, 6.0, 0.1);
        row.gainSlider.setValue(0.0);
        row.gainSlider.setTextBoxStyle(juce::Slider::NoTextBox, true, 0, 0);
        row.gainSlider.setColour(juce::Slider::trackColourId, kAccentSoft);
        row.gainSlider.setColour(juce::Slider::thumbColourId, kAccent);
        row.gainSlider.addListener(this);
        addAndMakeVisible(row.gainSlider);

        row.gainLabel.setText("0 dB", juce::dontSendNotification);
        row.gainLabel.setColour(juce::Label::textColourId, kTextMuted);
        row.gainLabel.setJustificationType(juce::Justification::centredRight);
        addAndMakeVisible(row.gainLabel);

        row.midiOutBox.setColour(juce::ComboBox::backgroundColourId, juce::Colour(0xff0f172a));
        row.midiOutBox.setColour(juce::ComboBox::outlineColourId, kPanelBorder);
        row.midiOutBox.setColour(juce::ComboBox::textColourId, kTextMain);
        for (int out = 1; out <= 7; ++out)
            row.midiOutBox.addItem("Out " + juce::String(out), out);
        row.midiOutBox.setSelectedId(static_cast<int>(i) + 1);
        addAndMakeVisible(row.midiOutBox);

        styleOutlineButton(row.generateButton);
        row.generateButton.addListener(this);
        addAndMakeVisible(row.generateButton);
    }

    humanizeTitleLabel.setText("HUMANIZE", juce::dontSendNotification);
    humanizeTitleLabel.setColour(juce::Label::textColourId, kTextMain);
    addAndMakeVisible(humanizeTitleLabel);

    humanizeHintLabel.setText("Add natural variation to generated MIDI", juce::dontSendNotification);
    humanizeHintLabel.setColour(juce::Label::textColourId, kTextMuted);
    addAndMakeVisible(humanizeHintLabel);

    humanizeSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    humanizeSlider.setRange(0.0, 100.0, 1.0);
    humanizeSlider.setValue(60.0);
    humanizeSlider.setTextBoxStyle(juce::Slider::NoTextBox, true, 0, 0);
    humanizeSlider.setColour(juce::Slider::trackColourId, kAccentSoft);
    humanizeSlider.setColour(juce::Slider::thumbColourId, kAccent);
    humanizeSlider.addListener(this);
    addAndMakeVisible(humanizeSlider);

    humanizeValueLabel.setColour(juce::Label::textColourId, kTextMain);
    humanizeValueLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(humanizeValueLabel);

    stylePrimaryButton(masterGenerateButton);
    masterGenerateButton.addListener(this);
    addAndMakeVisible(masterGenerateButton);

    styleOutlineButton(exportButton);
    exportButton.addListener(this);
    addAndMakeVisible(exportButton);

    exportHintLabel.setText("Export all generated tracks as MIDI files", juce::dontSendNotification);
    exportHintLabel.setColour(juce::Label::textColourId, kTextMuted);
    exportHintLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(exportHintLabel);

    styleSmallButton(settingsButton);
    settingsButton.addListener(this);
    addAndMakeVisible(settingsButton);

    footerLabel.setText("ⓘ  Generate high-quality MIDI accompaniments using AI. Built for creativity.", juce::dontSendNotification);
    footerLabel.setColour(juce::Label::textColourId, kTextMuted);
    addAndMakeVisible(footerLabel);

    updatePromptCounter();
    sliderValueChanged(&humanizeSlider);
    syncUiState();
}

MidiSketchpadAudioProcessorEditor::~MidiSketchpadAudioProcessorEditor()
{
    disconnectButton.removeListener(this);
    importMidiButton.removeListener(this);
    generateChordsButton.removeListener(this);
    bpmMinusButton.removeListener(this);
    bpmPlusButton.removeListener(this);
    randomizeButton.removeListener(this);
    masterGenerateButton.removeListener(this);
    exportButton.removeListener(this);
    settingsButton.removeListener(this);
    for (auto& row : trackRows)
    {
        row.generateButton.removeListener(this);
        row.gainSlider.removeListener(this);
    }
    humanizeSlider.removeListener(this);
    promptEditor.removeListener(this);
    seedEditor.removeListener(this);
}

void MidiSketchpadAudioProcessorEditor::paint(juce::Graphics& g)
{
    juce::ColourGradient gradient(juce::Colour(0xff060b17), 0.0f, 0.0f, juce::Colour(0xff0b1220), 0.0f, (float) getHeight(), false);
    g.setGradientFill(gradient);
    g.fillAll();

    auto layout = calculateLayout();

    drawPanel(g, layout.chordsPanel, "1. CHORD PROGRESSION", kAccent);
    drawPanel(g, layout.stylePanel, "2. MUSIC STYLE & GLOBAL SETTINGS", kAccent);
    drawPanel(g, layout.tracksPanel, "3. TRACKS", kAccent);

    g.setColour(kPanelBg.withAlpha(0.7f));
    g.fillRoundedRectangle(layout.bottomRow.toFloat(), 10.0f);
    g.setColour(kPanelBorder);
    g.drawRoundedRectangle(layout.bottomRow.toFloat(), 10.0f, 1.0f);

    g.setColour(kPanelBg.withAlpha(0.7f));
    g.fillRoundedRectangle(layout.footer.toFloat(), 8.0f);
    g.setColour(kPanelBorder);
    g.drawRoundedRectangle(layout.footer.toFloat(), 8.0f, 1.0f);

    g.setColour(juce::Colour(0xff1e3a8a).withAlpha(0.35f));
    auto notice = layout.stylePanel.withTrimmedLeft(20).withTrimmedRight(20).removeFromBottom(56).reduced(0, 8);
    g.fillRoundedRectangle(notice.toFloat(), 8.0f);

    g.setColour(juce::Colours::black.withAlpha(0.25f));
    g.fillRoundedRectangle(layout.masterButton.toFloat().expanded(4.0f), 12.0f);
}

void MidiSketchpadAudioProcessorEditor::resized()
{
    auto layout = calculateLayout();

    auto headerBody = layout.header.reduced(14, 10);
    auto leftHeader = headerBody.removeFromLeft(520);
    titleLabel.setBounds(leftHeader.removeFromTop(34));
    subtitleLabel.setBounds(leftHeader.removeFromTop(18));

    auto rightHeader = headerBody.removeFromRight(370);
    lmStudioLabel.setBounds(rightHeader.removeFromLeft(110));
    lmStatusLabel.setBounds(rightHeader.removeFromLeft(130));
    disconnectButton.setBounds(rightHeader.removeFromLeft(110).reduced(8, 0));

    auto chord = layout.chordsPanel.reduced(16, 16);
    chord.removeFromTop(30);
    chordCaptionLabel.setBounds(chord.removeFromTop(24));
    chordsEditor.setBounds(chord.removeFromTop(180));
    chordHelpLabel.setBounds(chord.removeFromTop(26));
    importMidiButton.setBounds(chord.removeFromTop(32).withWidth(170));
    chord.removeFromTop(16);
    generateChordsButton.setBounds(chord.removeFromTop(44).withWidth(240));

    auto style = layout.stylePanel.reduced(16, 16);
    style.removeFromTop(30);
    promptCaptionLabel.setBounds(style.removeFromTop(24));
    auto promptArea = style.removeFromTop(180);
    promptEditor.setBounds(promptArea);
    promptCountLabel.setBounds(promptArea.removeFromBottom(22).reduced(8, 0));

    style.removeFromTop(8);
    auto bpmRow = style.removeFromTop(58);
    auto bpmArea = bpmRow.removeFromLeft(170);
    bpmLabel.setBounds(bpmArea.removeFromTop(18));
    auto bpmControls = bpmArea.removeFromTop(34);
    bpmMinusButton.setBounds(bpmControls.removeFromLeft(34));
    bpmValueLabel.setBounds(bpmControls.removeFromLeft(70).reduced(4, 0));
    bpmPlusButton.setBounds(bpmControls.removeFromLeft(34));

    auto timeArea = bpmRow.reduced(8, 0);
    timeSigLabel.setBounds(timeArea.removeFromTop(18));
    auto sigControls = timeArea.removeFromTop(34);
    timeSigNumBox.setBounds(sigControls.removeFromLeft(54));
    slashLabel.setBounds(sigControls.removeFromLeft(16));
    timeSigDenBox.setBounds(sigControls.removeFromLeft(54));

    style.removeFromTop(6);
    seedLabel.setBounds(style.removeFromTop(22));
    auto seedRow = style.removeFromTop(34);
    seedEditor.setBounds(seedRow.removeFromLeft(120));
    seedRow.removeFromLeft(8);
    randomizeButton.setBounds(seedRow.removeFromLeft(118));

    auto noticeArea = layout.stylePanel.withTrimmedLeft(20).withTrimmedRight(20).removeFromBottom(56).reduced(8, 12);
    seedNoticeLabel.setBounds(noticeArea);

    auto tracks = layout.tracksPanel.reduced(16, 16);
    tracks.removeFromTop(34);
    auto tracksHeader = tracks.removeFromTop(22);
    tracksHeader.removeFromLeft(340);
    tracksHeaderEnableLabel.setBounds(tracksHeader.removeFromLeft(70));
    tracksHeaderOutputLabel.setBounds(tracksHeader.removeFromLeft(110));
    tracksHeaderGenerateLabel.setBounds(tracksHeader.removeFromLeft(90));

    tracks.removeFromTop(4);
    const int rowHeight = 44;
    for (auto& row : trackRows)
    {
        auto rowArea = tracks.removeFromTop(rowHeight);
        row.nameLabel.setBounds(rowArea.removeFromLeft(235));
        row.enableToggle.setBounds(rowArea.removeFromLeft(70).reduced(10, 10));
        auto gainArea = rowArea.removeFromLeft(130);
        row.gainSlider.setBounds(gainArea.removeFromTop(20));
        row.gainLabel.setBounds(gainArea.removeFromTop(18));
        rowArea.removeFromLeft(4);
        row.midiOutBox.setBounds(rowArea.removeFromLeft(100).reduced(0, 7));
        rowArea.removeFromLeft(8);
        row.generateButton.setBounds(rowArea.removeFromLeft(110).reduced(0, 7));
        tracks.removeFromTop(6);
    }

    auto bottom = layout.bottomRow.reduced(14, 10);
    auto human = bottom.removeFromLeft(370);
    humanizeTitleLabel.setBounds(human.removeFromTop(20));
    humanizeHintLabel.setBounds(human.removeFromTop(18));
    auto sliderArea = human.removeFromTop(20);
    humanizeSlider.setBounds(sliderArea.removeFromLeft(260));
    humanizeValueLabel.setBounds(sliderArea.removeFromLeft(54));

    bottom.removeFromLeft(8);
    masterGenerateButton.setBounds(bottom.removeFromLeft(330).reduced(0, 2));

    bottom.removeFromLeft(12);
    auto exportArea = bottom.removeFromLeft(220);
    exportButton.setBounds(exportArea.removeFromTop(40));
    exportHintLabel.setBounds(exportArea.removeFromTop(20));

    bottom.removeFromLeft(12);
    settingsButton.setBounds(bottom.removeFromLeft(92).reduced(8, 8));

    footerLabel.setBounds(layout.footer.reduced(12, 0));
}

MidiSketchpadAudioProcessorEditor::LayoutRects MidiSketchpadAudioProcessorEditor::calculateLayout() const
{
    LayoutRects r;

    auto bounds = getLocalBounds().reduced(10, 10);
    r.header = bounds.removeFromTop(62);
    bounds.removeFromTop(10);

    r.sectionRow = bounds.removeFromTop(470);
    bounds.removeFromTop(10);

    r.bottomRow = bounds.removeFromTop(84);
    bounds.removeFromTop(8);
    r.footer = bounds.removeFromTop(34);

    auto left = r.sectionRow;
    r.chordsPanel = left.removeFromLeft(static_cast<int>(r.sectionRow.getWidth() * 0.30f));
    left.removeFromLeft(10);
    r.stylePanel = left.removeFromLeft(static_cast<int>(r.sectionRow.getWidth() * 0.28f));
    left.removeFromLeft(10);
    r.tracksPanel = left;

    auto action = r.bottomRow.reduced(14, 10);
    r.humanizePanel = action.removeFromLeft(370);
    action.removeFromLeft(8);
    r.masterButton = action.removeFromLeft(330);
    action.removeFromLeft(12);
    r.exportPanel = action.removeFromLeft(220);
    action.removeFromLeft(12);
    r.settingsButton = action.removeFromLeft(92);

    return r;
}

void MidiSketchpadAudioProcessorEditor::drawPanel(juce::Graphics& g, juce::Rectangle<int> area, juce::StringRef title, juce::Colour accent) const
{
    g.setColour(kPanelBg.withAlpha(0.86f));
    g.fillRoundedRectangle(area.toFloat(), 10.0f);

    g.setColour(kPanelBorder);
    g.drawRoundedRectangle(area.toFloat(), 10.0f, 1.0f);

    g.setColour(accent.withAlpha(0.95f));
    g.setFont(juce::Font(15.0f, juce::Font::bold));
    g.drawText(title, area.removeFromTop(30).reduced(14, 2), juce::Justification::centredLeft, false);
}

void MidiSketchpadAudioProcessorEditor::stylePrimaryButton(juce::TextButton& button)
{
    button.setColour(juce::TextButton::buttonColourId, juce::Colour(0xff2563eb));
    button.setColour(juce::TextButton::buttonOnColourId, juce::Colour(0xff1d4ed8));
    button.setColour(juce::TextButton::textColourOffId, juce::Colours::white);
    button.setColour(juce::TextButton::textColourOnId, juce::Colours::white);
}

void MidiSketchpadAudioProcessorEditor::styleOutlineButton(juce::TextButton& button)
{
    button.setColour(juce::TextButton::buttonColourId, juce::Colour(0xff0f172a));
    button.setColour(juce::TextButton::buttonOnColourId, juce::Colour(0xff0b2230));
    button.setColour(juce::TextButton::textColourOffId, kAccent);
    button.setColour(juce::TextButton::textColourOnId, kAccent);
    button.setColour(juce::TextButton::outlineColourId, kAccentSoft.withAlpha(0.65f));
    button.setConnectedEdges(juce::Button::ConnectedOnNone);
}

void MidiSketchpadAudioProcessorEditor::styleSmallButton(juce::TextButton& button)
{
    button.setColour(juce::TextButton::buttonColourId, juce::Colour(0xff0f172a));
    button.setColour(juce::TextButton::buttonOnColourId, juce::Colour(0xff1e293b));
    button.setColour(juce::TextButton::textColourOffId, kTextMain);
    button.setColour(juce::TextButton::textColourOnId, kTextMain);
}

void MidiSketchpadAudioProcessorEditor::styleEditor(juce::TextEditor& editor, bool multiLine)
{
    editor.setMultiLine(multiLine);
    editor.setReturnKeyStartsNewLine(multiLine);
    editor.setColour(juce::TextEditor::backgroundColourId, juce::Colour(0xff0b1220));
    editor.setColour(juce::TextEditor::outlineColourId, kPanelBorder);
    editor.setColour(juce::TextEditor::textColourId, kTextMain);
    editor.setColour(juce::TextEditor::highlightColourId, kAccentSoft.withAlpha(0.35f));
}

void MidiSketchpadAudioProcessorEditor::updatePromptCounter()
{
    promptCountLabel.setText(juce::String(promptEditor.getText().length()) + " / 200", juce::dontSendNotification);
}

void MidiSketchpadAudioProcessorEditor::syncUiState()
{
    auto& state = processorRef.getUiState();
    state.setProperty("chords", chordsEditor.getText(), nullptr);
    state.setProperty("prompt", promptEditor.getText(), nullptr);
    state.setProperty("bpm", bpmValueLabel.getText().getIntValue(), nullptr);
    state.setProperty("time_sig_num", timeSigNumBox.getSelectedId(), nullptr);
    state.setProperty("time_sig_den", timeSigDenBox.getSelectedId(), nullptr);
    state.setProperty("seed", seedEditor.getText().getIntValue(), nullptr);
    state.setProperty("humanize", (int) std::round(humanizeSlider.getValue()), nullptr);
}

void MidiSketchpadAudioProcessorEditor::buttonClicked(juce::Button* button)
{
    if (button == &bpmMinusButton || button == &bpmPlusButton)
    {
        auto bpm = bpmValueLabel.getText().getIntValue();
        bpm += (button == &bpmPlusButton ? 1 : -1);
        bpm = juce::jlimit(40, 240, bpm);
        bpmValueLabel.setText(juce::String(bpm), juce::dontSendNotification);
        syncUiState();
        return;
    }

    if (button == &randomizeButton)
    {
        seedEditor.setText(juce::String(juce::Random::getSystemRandom().nextInt({ 10000, 99999 })), false);
        syncUiState();
        return;
    }

    if (button == &masterGenerateButton)
    {
        footerLabel.setText("ⓘ  Generating all enabled tracks...", juce::dontSendNotification);
        syncUiState();
        return;
    }

    if (button == &generateChordsButton)
    {
        footerLabel.setText("ⓘ  Generating chord suggestions from prompt...", juce::dontSendNotification);
        return;
    }

    if (button == &importMidiButton)
    {
        footerLabel.setText("ⓘ  Import MIDI file action is prepared (bridge wiring next).", juce::dontSendNotification);
        return;
    }

    if (button == &exportButton)
    {
        footerLabel.setText("ⓘ  Export all MIDI action is prepared.", juce::dontSendNotification);
        return;
    }

    if (button == &settingsButton)
    {
        footerLabel.setText("ⓘ  Settings dialog scaffold is ready for next step.", juce::dontSendNotification);
        return;
    }

    if (button == &disconnectButton)
    {
        lmStatusLabel.setText("● DISCONNECTED", juce::dontSendNotification);
        lmStatusLabel.setColour(juce::Label::textColourId, juce::Colour(0xfff59e0b));
        footerLabel.setText("ⓘ  LM Studio connection toggled (mock state).", juce::dontSendNotification);
        return;
    }

    for (size_t i = 0; i < trackRows.size(); ++i)
    {
        if (button == &trackRows[i].generateButton)
        {
            footerLabel.setText("ⓘ  Generate track: " + kTrackNames[i], juce::dontSendNotification);
            return;
        }
    }
}

void MidiSketchpadAudioProcessorEditor::sliderValueChanged(juce::Slider* slider)
{
    if (slider == &humanizeSlider)
    {
        humanizeValueLabel.setText(juce::String((int) std::round(humanizeSlider.getValue())) + "%", juce::dontSendNotification);
        syncUiState();
        return;
    }

    for (auto& row : trackRows)
    {
        if (slider == &row.gainSlider)
        {
            row.gainLabel.setText(juce::String(row.gainSlider.getValue(), 1) + " dB", juce::dontSendNotification);
            return;
        }
    }
}

void MidiSketchpadAudioProcessorEditor::textEditorTextChanged(juce::TextEditor& editor)
{
    if (&editor == &promptEditor)
        updatePromptCounter();

    syncUiState();
}
