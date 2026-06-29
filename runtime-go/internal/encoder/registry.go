package encoder

import (
	"fmt"
	"sort"
)

var encoders = map[string]Encoder{}

// Register adds an encoder under the given name.
func Register(name string, enc Encoder) {
	encoders[name] = enc
}

// Get returns the encoder registered under name.
func Get(name string) (Encoder, error) {
	enc, ok := encoders[name]
	if !ok {
		return nil, fmt.Errorf("unknown encoder: %s", name)
	}
	return enc, nil
}

// List returns all registered encoder names sorted.
func List() []string {
	names := make([]string, 0, len(encoders))
	for name := range encoders {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}
