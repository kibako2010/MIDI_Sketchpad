#include "PluginProcessor.h"
#include "PluginEditor.h"

MidiSketchpadAudioProcessor::MidiSketchpadAudioProcessor()
#ifndef JucePlugin_PreferredChannelConfigurations
    : AudioProcessor(BusesProperties().withInput("Input", juce::AudioChannelSet::stereo(), true)
                                     .withOutput("Output", juce::AudioChannelSet::stereo(), true))
#endif
{
    uiState.setProperty("version", 1, nullptr);
    uiState.setProperty("chords", "Am | F | C | G", nullptr);
    uiState.setProperty("prompt", "アニメ風アイリッシュ。明るく疾走感。", nullptr);
    uiState.setProperty("bpm", 120, nullptr);
    uiState.setProperty("time_sig_num", 6, nullptr);
    uiState.setProperty("time_sig_den", 8, nullptr);
    uiState.setProperty("bars", 16, nullptr);
    uiState.setProperty("seed", 12345, nullptr);
    uiState.setProperty("humanize", 60, nullptr);
}

MidiSketchpadAudioProcessor::~MidiSketchpadAudioProcessor() = default;

const juce::String MidiSketchpadAudioProcessor::getName() const { return JucePlugin_Name; }

bool MidiSketchpadAudioProcessor::acceptsMidi() const { return false; }
bool MidiSketchpadAudioProcessor::producesMidi() const { return false; }
bool MidiSketchpadAudioProcessor::isMidiEffect() const { return false; }
double MidiSketchpadAudioProcessor::getTailLengthSeconds() const { return 0.0; }

int MidiSketchpadAudioProcessor::getNumPrograms() { return 1; }
int MidiSketchpadAudioProcessor::getCurrentProgram() { return 0; }
void MidiSketchpadAudioProcessor::setCurrentProgram(int) {}
const juce::String MidiSketchpadAudioProcessor::getProgramName(int) { return {}; }
void MidiSketchpadAudioProcessor::changeProgramName(int, const juce::String&) {}

void MidiSketchpadAudioProcessor::prepareToPlay(double, int) {}
void MidiSketchpadAudioProcessor::releaseResources() {}

bool MidiSketchpadAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    return layouts.getMainOutputChannelSet() == juce::AudioChannelSet::mono()
        || layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
}

void MidiSketchpadAudioProcessor::processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&)
{
    // v0.1: no-op (audio threadで重い処理禁止)
}

bool MidiSketchpadAudioProcessor::hasEditor() const { return true; }
juce::AudioProcessorEditor* MidiSketchpadAudioProcessor::createEditor() { return new MidiSketchpadAudioProcessorEditor(*this); }

void MidiSketchpadAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto stateVar = juce::var(uiState.createXml()->toString());
    auto json = juce::JSON::toString(stateVar);
    destData.append(json.toRawUTF8(), json.getNumBytesAsUTF8());
}

void MidiSketchpadAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    auto json = juce::String::fromUTF8(static_cast<const char*>(data), sizeInBytes);
    auto parsed = juce::JSON::parse(json);
    if (parsed.isString())
    {
        auto xmlText = parsed.toString();
        std::unique_ptr<juce::XmlElement> xml(juce::XmlDocument::parse(xmlText));
        if (xml != nullptr)
            uiState = juce::ValueTree::fromXml(*xml);
    }
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new MidiSketchpadAudioProcessor();
}
