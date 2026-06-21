#include "PluginSettings.h"

juce::var PluginSettings::toVar() const
{
    auto* obj = new juce::DynamicObject();
    obj->setProperty("python_executable", pythonExecutable);
    obj->setProperty("backend_script", backendScript);
    obj->setProperty("lm_studio_api_url", lmStudioApiUrl);
    obj->setProperty("default_output_dir", defaultOutputDir);
    obj->setProperty("open_folder_after_generate", openFolderAfterGenerate);
    obj->setProperty("create_timestamp_folder", createTimestampFolder);
    obj->setProperty("merge", merge);
    obj->setProperty("language", language);
    return juce::var(obj);
}

PluginSettings PluginSettings::fromVar(const juce::var& value)
{
    PluginSettings s;
    if (auto* obj = value.getDynamicObject())
    {
        s.pythonExecutable = obj->getProperty("python_executable", s.pythonExecutable).toString();
        s.backendScript = obj->getProperty("backend_script", s.backendScript).toString();
        s.lmStudioApiUrl = obj->getProperty("lm_studio_api_url", s.lmStudioApiUrl).toString();
        s.defaultOutputDir = obj->getProperty("default_output_dir", s.defaultOutputDir).toString();
        s.openFolderAfterGenerate = static_cast<bool>(obj->getProperty("open_folder_after_generate", s.openFolderAfterGenerate));
        s.createTimestampFolder = static_cast<bool>(obj->getProperty("create_timestamp_folder", s.createTimestampFolder));
        s.merge = static_cast<bool>(obj->getProperty("merge", s.merge));
        s.language = obj->getProperty("language", s.language).toString();
    }
    return s;
}

juce::File PluginSettingsStore::getSettingsFile() const
{
    auto appData = juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory);
    auto dir = appData.getChildFile("MIDI Sketchpad");
    dir.createDirectory();
    return dir.getChildFile("settings.json");
}

PluginSettings PluginSettingsStore::load() const
{
    auto file = getSettingsFile();
    if (! file.existsAsFile())
        return {};

    auto parsed = juce::JSON::parse(file.loadFileAsString());
    return PluginSettings::fromVar(parsed);
}

bool PluginSettingsStore::save(const PluginSettings& settings) const
{
    auto file = getSettingsFile();
    return file.replaceWithText(juce::JSON::toString(settings.toVar()), false, false, "\n");
}
