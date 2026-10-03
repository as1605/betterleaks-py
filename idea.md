Here is a structured, step-by-step plan to establish the `betterleaks-py` repository, aggressively test the `gopy` automated bindings, and seamlessly pivot to a `cgo` + `ctypes` implementation if `gopy` hits a wall.

Structuring the GitHub repository with a submodule ensures both approaches pull from the exact same upstream source, keeping your Python data pipelines and package distribution workflows clean.

### Phase 1: Repository Setup

First, initialize the boundary between Python and Go.

1. **Initialize `betterleaks-py**`:
Create the new repository and set up a standard Python package layout.
```bash
mkdir betterleaks-py && cd betterleaks-py
git init
mkdir -p src/betterleaks wrapper tests

```


2. **Add Betterleaks as a Submodule**:
Pull in the Go engine so the local Go compiler can access it directly.
```bash
git submodule add https://github.com/betterleaks/betterleaks.git upstream

```


3. **Initialize the Wrapper Module**:
Initialize a Go module for the wrapper code that will bridge the gap.
```bash
cd wrapper
go mod init github.com/yourusername/betterleaks-py/wrapper
go get github.com/betterleaks/betterleaks@latest

```



---

### Phase 2: The `gopy` Experiment (Primary Attempt)

The goal here is to give `gopy` the easiest possible Go code to parse. You cannot point `gopy` at the core `betterleaks` packages because of the complex interfaces. You must build a simplified API.

**Step 1: Write the `gopy` Wrapper (`wrapper/gopy_wrapper.go`)**
Create a Go file that imports the upstream core and exposes a strictly typed, simplified struct. Avoid interfaces, channels, and complex pointers in this file.

```go
package betterleaks_wrapper

import (
    "github.com/betterleaks/betterleaks/scan" // adjust based on internal API
)

// Simplified struct for gopy to parse
type ScanResult struct {
    File    string
    RuleID  string
    Secret  string
}

func ScanString(content string) []ScanResult {
    // 1. Initialize betterleaks engine
    // 2. Scan the string
    // 3. Map complex internal findings to []ScanResult
    // 4. Return the simplified slice
}

```

**Step 2: Generate the Bindings**
Install `gopy` and its C-level dependencies (`pkg-config`, `python3-dev`). Then attempt to compile.

```bash
go install github.com/go-python/gopy@latest
gopy build -output=../src/betterleaks -vm=python3 ./wrapper

```

**Step 3: The Stress Test**
If the build succeeds (which generates a `.so` file inside `src/betterleaks`), drop into a Python REPL to test memory stability.

```python
import betterleaks.betterleaks_wrapper as bl

# Test 1: Can it instantiate the generated classes?
results = bl.ScanString("my secret is GITHUB_PAT_1234567890")

# Test 2: Does it survive garbage collection?
import gc
del results
gc.collect() 
# If the Python interpreter segfaults here, gopy's memory boundary has failed.

```

**Evaluation:**
If it builds cleanly, doesn't segfault on garbage collection, and successfully returns the data, proceed to write `setup.py` to package it. If it fails to compile due to unsupported types, or segfaults during the stress test, abandon `gopy` and move immediately to Phase 3.

---

### Phase 3: The `cgo` Fallback (Robust Implementation)

If `gopy` proves unstable, `cgo` provides complete control over the memory boundary using JSON as the transport mechanism.

**Step 1: Write the C-Shared Export (`wrapper/cgo_wrapper.go`)**
Replace the wrapper file with one that strictly adheres to the C ABI.

```go
package main

/*
#include <stdlib.h>
*/
import "C"
import (
    "encoding/json"
    "unsafe"
    // import betterleaks internal engine
)

//export ScanStringCGO
func ScanStringCGO(content *C.char) *C.char {
    goString := C.GoString(content)
    
    // 1. Run betterleaks scan on goString
    // 2. Get results
    
    // Convert results to JSON to avoid complex C-struct mapping
    jsonBytes, _ := json.Marshal(results)
    return C.CString(string(jsonBytes))
}

//export FreeMemory
func FreeMemory(ptr *C.char) {
    C.free(unsafe.Pointer(ptr))
}

func main() {}

```

**Step 2: Compile the Shared Library**
Compile the Go code into a shared C library.

```bash
go build -buildmode=c-shared -o ../src/betterleaks/libbetterleaks.so cgo_wrapper.go

```

**Step 3: Construct the Python `ctypes` Wrapper**
In `src/betterleaks/__init__.py`, write the native Python wrapper to load the library and handle the memory allocation safely.

```python
import ctypes
import json
import os

# Load the shared library
lib_path = os.path.join(os.path.dirname(__file__), "libbetterleaks.so")
lib = ctypes.CDLL(lib_path)

# Define C argument and return types
lib.ScanStringCGO.argtypes = [ctypes.c_char_p]
lib.ScanStringCGO.restype = ctypes.c_void_p  # Return void pointer to prevent auto-conversion

lib.FreeMemory.argtypes = [ctypes.c_void_p]

def scan_string(content: str) -> dict:
    encoded_content = content.encode('utf-8')
    
    # Call Go function
    ptr = lib.ScanStringCGO(encoded_content)
    
    try:
        # Read the C-string pointer
        json_bytes = ctypes.cast(ptr, ctypes.c_char_p).value
        # Parse the JSON back into a Python dictionary
        return json.loads(json_bytes.decode('utf-8'))
    finally:
        # Guarantee memory is freed on the Go/C side to prevent leaks
        if ptr:
            lib.FreeMemory(ptr)

```

### Phase 4: Packaging and Publishing

Once either method successfully passes unit testing via `pytest`, construct the `pyproject.toml` or `setup.py` to trigger the `go build` step before building the Python wheel (`.whl`). Using `cibuildwheel` in a GitHub Actions workflow will allow you to cross-compile the Go binary for Linux, macOS, and Windows and push the unified package to PyPI.
