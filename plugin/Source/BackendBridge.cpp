#include "BackendBridge.h"

BackendBridge::BackendBridge(Config cfg)
    : config(std::move(cfg))
{
}

void BackendBridge::setConfig(const Config& cfg)
{
    config = cfg;
}

juce::var BackendBridge::executeRequest(const juce::var& request, int timeoutMs, juce::String& errorMessage) const
{
    if (config.pythonExecutable.isEmpty())
    {
        errorMessage = "Python executable が未設定です";
        return {};
    }
    if (config.backendScriptPath.isEmpty())
    {
        errorMessage = "backend script path が未設定です";
        return {};
    }

    juce::TemporaryFile requestFile("request.json");
    juce::TemporaryFile responseFile("response.json");

    auto reqPath = requestFile.getFile();
    auto resPath = responseFile.getFile();

    if (! reqPath.replaceWithText(juce::JSON::toString(request), false, false, "\n"))
    {
        errorMessage = "request.json の書き込みに失敗しました";
        return {};
    }

    juce::StringArray args;
    args.add(config.pythonExecutable.quoted());
    args.add(config.backendScriptPath.quoted());
    args.add("--request");
    args.add(reqPath.getFullPathName().quoted());
    args.add("--response");
    args.add(resPath.getFullPathName().quoted());

    juce::ChildProcess process;
    if (! process.start(args.joinIntoString(" ")))
    {
        errorMessage = "Python process の起動に失敗しました";
        return {};
    }

    if (! process.waitForProcessToFinish(timeoutMs))
    {
        process.kill();
        errorMessage = "Backend timeout";
        return {};
    }

    if (! resPath.existsAsFile())
    {
        errorMessage = "response.json が存在しません";
        return {};
    }

    auto parsed = juce::JSON::parse(resPath);
    if (parsed.isVoid())
    {
        errorMessage = "response.json のJSONパースに失敗しました";
        return {};
    }

    return parsed;
}
