#pragma once

#include <juce_core/juce_core.h>

struct PluginSettings
{
    juce::String pythonExecutable { "python" };
    juce::String backendScript;
    juce::String lmStudioApiUrl { "http://localhost:1234/v1/chat/completions" };
    juce::String defaultOutputDir;
    bool openFolderAfterGenerate { false };
    bool createTimestampFolder { true };
    bool merge { true };
    juce::String language { "ja" };

    juce::var toVar() const;
    static PluginSettings fromVar(const juce::var& value);
};

class PluginSettingsStore
{
public:
    PluginSettings load() const;
    bool save(const PluginSettings& settings) const;

private:
    juce::File getSettingsFile() const;
};
