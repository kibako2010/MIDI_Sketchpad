#include "JsonUtil.h"

namespace JsonUtil
{
juce::String toString(const juce::var& value)
{
    return juce::JSON::toString(value);
}

juce::var parse(const juce::String& jsonText)
{
    return juce::JSON::parse(jsonText);
}
}
