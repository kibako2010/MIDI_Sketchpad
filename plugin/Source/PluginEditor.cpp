#include "PluginEditor.h"

MidiSketchpadAudioProcessorEditor::MidiSketchpadAudioProcessorEditor(MidiSketchpadAudioProcessor& p)
    : AudioProcessorEditor(&p), processorRef(p)
{
    setSize(860, 620);

    title.setText("MIDI Sketchpad v0.1 AI支援 MIDI伴奏ジェネレーター", juce::dontSendNotification);
    title.setJustificationType(juce::Justification::centredLeft);
    addAndMakeVisible(title);

    chordsEditor.setMultiLine(true);
    chordsEditor.setText("Am | F | C | G", false);
    addAndMakeVisible(chordsEditor);

    promptEditor.setMultiLine(true);
    promptEditor.setText("例: アニメ風アイリッシュ。明るく疾走感。フィドルとホイッスル中心。", false);
    addAndMakeVisible(promptEditor);

    generateButton.addListener(this);
    addAndMakeVisible(generateButton);

    statusLabel.setText("Python Backend: 未接続", juce::dontSendNotification);
    addAndMakeVisible(statusLabel);
}

MidiSketchpadAudioProcessorEditor::~MidiSketchpadAudioProcessorEditor()
{
    generateButton.removeListener(this);
}

void MidiSketchpadAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour(0xff1e1e1e));
    g.setColour(juce::Colours::white);
    g.setFont(15.0f);
    g.drawText("1. コード進行", 16, 52, 200, 24, juce::Justification::left);
    g.drawText("2. 音楽スタイル / 全体設定", 16, 250, 280, 24, juce::Justification::left);
}

void MidiSketchpadAudioProcessorEditor::resized()
{
    title.setBounds(12, 10, getWidth() - 24, 30);
    chordsEditor.setBounds(16, 80, getWidth() - 32, 150);
    promptEditor.setBounds(16, 280, getWidth() - 32, 150);
    generateButton.setBounds(getWidth() - 180, getHeight() - 56, 160, 36);
    statusLabel.setBounds(16, getHeight() - 50, getWidth() - 220, 24);
}

void MidiSketchpadAudioProcessorEditor::buttonClicked(juce::Button* button)
{
    if (button == &generateButton)
    {
        generateButton.setEnabled(false);
        statusLabel.setText("生成中...", juce::dontSendNotification);
        // TODO: BackendBridgeをバックグラウンドスレッドで呼ぶ。
        generateButton.setEnabled(true);
        statusLabel.setText("生成準備完了", juce::dontSendNotification);
    }
}
