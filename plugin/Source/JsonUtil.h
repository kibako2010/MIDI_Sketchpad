#pragma once

#include <juce_core/juce_core.h>

namespace JsonUtil
{
    juce::String toString(const juce::var& value);
    juce::var parse(const juce::String& jsonText);
}
