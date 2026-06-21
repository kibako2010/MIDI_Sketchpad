#pragma once

#include <juce_core/juce_core.h>

class BackendBridge
{
public:
    struct Config
    {
        juce::String pythonExecutable { "python" };
        juce::String backendScriptPath;
    };

    explicit BackendBridge(Config cfg = {});

    void setConfig(const Config& cfg);
    const Config& getConfig() const noexcept { return config; }

    juce::var executeRequest(const juce::var& request, int timeoutMs, juce::String& errorMessage) const;

private:
    Config config;
};
