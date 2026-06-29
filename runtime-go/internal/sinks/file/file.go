package file

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// Sink appends events to a JSONL file.
type Sink struct {
	path       string
	outputDir  string
	file       *os.File
	count      int
	failed     int
}

// New creates a file sink constrained to outputDir.
func New(path, outputDir string) *Sink { return &Sink{path: path, outputDir: outputDir} }

// ValidatePath checks that path is contained within outputDir without side effects.
func ValidatePath(path, outputDir string) error {
	_, err := resolveWithinOutputDir(path, outputDir)
	return err
}

// resolveWithinOutputDir resolves the target path against outputDir and ensures
// the result is contained within outputDir.
func resolveWithinOutputDir(target, outputDir string) (string, error) {
	base, err := filepath.Abs(outputDir)
	if err != nil {
		return "", fmt.Errorf("resolve output directory: %w", err)
	}

	var resolved string
	if filepath.IsAbs(target) {
		resolved, err = filepath.EvalSymlinks(target)
		if err != nil {
			resolved = filepath.Clean(target)
		}
	} else {
		resolved, err = filepath.EvalSymlinks(filepath.Join(base, target))
		if err != nil {
			resolved = filepath.Clean(filepath.Join(base, target))
		}
	}

	rel, err := filepath.Rel(base, resolved)
	if err != nil || strings.HasPrefix(rel, "..") || rel == ".." {
		return "", fmt.Errorf("file sink path %q escapes output directory %q", target, outputDir)
	}
	return resolved, nil
}

// Open creates the parent directory and opens the file.
func (s *Sink) Open() error {
	resolved, err := resolveWithinOutputDir(s.path, s.outputDir)
	if err != nil {
		return err
	}
	s.path = resolved

	if err := os.MkdirAll(filepath.Dir(s.path), 0o755); err != nil {
		return err
	}
	file, err := os.OpenFile(s.path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	s.file = file
	return nil
}

// Write appends one event.
func (s *Sink) Write(ev event.Event) error {
	if s.file == nil {
		return fmt.Errorf("file sink is not open")
	}
	data, err := json.Marshal(ev)
	if err != nil {
		s.failed++
		return err
	}
	if _, err := s.file.Write(append(data, '\n')); err != nil {
		s.failed++
		return err
	}
	s.count++
	return nil
}

// Flush flushes the file.
func (s *Sink) Flush() error {
	if s.file == nil {
		return nil
	}
	return s.file.Sync()
}

// Close closes the file.
func (s *Sink) Close() error {
	if s.file == nil {
		return nil
	}
	return s.file.Close()
}

// Count returns emitted events.
func (s *Sink) Count() int { return s.count }

// Failed returns failed writes.
func (s *Sink) Failed() int { return s.failed }
