package main

/*
#include <stdlib.h>
*/
import "C"
import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"unsafe"

	"github.com/betterleaks/betterleaks/v2/config"
	"github.com/betterleaks/betterleaks/v2/report"
	"github.com/betterleaks/betterleaks/v2/scan"
)

type ScanResponse struct {
	Success bool             `json:"success"`
	Data    []report.Finding `json:"data"`
	Error   string           `json:"error,omitempty"`
}

var (
	defaultScannerOnce sync.Once
	defaultScanner     *scan.Scanner
	defaultScannerErr  error

	scannerCache sync.Map // map[string]*scan.Scanner
)

func getDefaultScanner() (*scan.Scanner, error) {
	defaultScannerOnce.Do(func() {
		cfg, err := config.Default()
		if err != nil {
			defaultScannerErr = fmt.Errorf("failed to load default config: %w", err)
			return
		}
		s, err := scan.New(cfg)
		if err != nil {
			defaultScannerErr = fmt.Errorf("failed to initialize scanner: %w", err)
			return
		}
		defaultScanner = s
	})
	return defaultScanner, defaultScannerErr
}

func getScannerForConfig(configPath string) (*scan.Scanner, error) {
	if configPath == "" {
		return getDefaultScanner()
	}
	if val, ok := scannerCache.Load(configPath); ok {
		return val.(*scan.Scanner), nil
	}
	cfg, err := config.LoadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to load config from %s: %w", configPath, err)
	}
	s, err := scan.New(cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize scanner with %s: %w", configPath, err)
	}
	scannerCache.Store(configPath, s)
	return s, nil
}

func marshalResponse(resp ScanResponse) *C.char {
	bytes, err := json.Marshal(resp)
	if err != nil {
		fallback := fmt.Sprintf(`{"success":false,"error":%q}`, err.Error())
		return C.CString(fallback)
	}
	return C.CString(string(bytes))
}

//export ScanStringCGO
func ScanStringCGO(content *C.char) *C.char {
	return ScanStringWithConfigCGO(content, nil)
}

//export ScanStringWithConfigCGO
func ScanStringWithConfigCGO(content *C.char, configPath *C.char) *C.char {
	if content == nil {
		return marshalResponse(ScanResponse{Success: false, Error: "content is null"})
	}
	goContent := C.GoString(content)
	goConfigPath := ""
	if configPath != nil {
		goConfigPath = C.GoString(configPath)
	}

	scanner, err := getScannerForConfig(goConfigPath)
	if err != nil {
		return marshalResponse(ScanResponse{Success: false, Error: err.Error()})
	}

	findings := scanner.ScanString(goContent)
	if findings == nil {
		findings = []report.Finding{}
	}
	return marshalResponse(ScanResponse{Success: true, Data: findings})
}

//export ScanFileCGO
func ScanFileCGO(filePath *C.char, configPath *C.char) *C.char {
	if filePath == nil {
		return marshalResponse(ScanResponse{Success: false, Error: "filePath is null"})
	}
	goFilePath := C.GoString(filePath)
	goConfigPath := ""
	if configPath != nil {
		goConfigPath = C.GoString(configPath)
	}

	data, err := os.ReadFile(goFilePath)
	if err != nil {
		return marshalResponse(ScanResponse{Success: false, Error: fmt.Sprintf("failed to read file %s: %v", goFilePath, err)})
	}

	scanner, err := getScannerForConfig(goConfigPath)
	if err != nil {
		return marshalResponse(ScanResponse{Success: false, Error: err.Error()})
	}

	findings := scanner.ScanString(string(data))
	if findings == nil {
		findings = []report.Finding{}
	}
	for i := range findings {
		if findings[i].Location.Path == "" {
			findings[i].Location.Path = goFilePath
		}
	}
	return marshalResponse(ScanResponse{Success: true, Data: findings})
}

//export FreeMemory
func FreeMemory(ptr *C.char) {
	if ptr != nil {
		C.free(unsafe.Pointer(ptr))
	}
}

func main() {}
