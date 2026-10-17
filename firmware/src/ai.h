#pragma once

#include <WString.h>

// Ask Vertex for one turn. registryJson is a JSON array of apps already on
// the device, or "[]". On success, turnJson is the inner propose, mutate, or
// say object and the function returns true.
//
// The key is GEMINI_API_KEY in gemini_key.h, copied from the repo-root .env.
// That header stays untracked. Without it, this returns false.
bool aiAsk(const char* text, const char* registryJson, String& turnJson);
