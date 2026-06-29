package encoder

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// enrichmentFile is the YAML file inside a pack that holds profiles.
const enrichmentFile = "encoders" + string(os.PathSeparator) + "enrichment.yaml"

// LoadEnrichmentProfiles loads enrichment profiles from a packs directory.
// It scans each pack subdirectory for encoders/enrichment.yaml.
func LoadEnrichmentProfiles(packsDir string) (map[string]EnrichmentProfile, error) {
	profiles := make(map[string]EnrichmentProfile)
	entries, err := os.ReadDir(packsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return profiles, nil
		}
		return nil, fmt.Errorf("read packs dir: %w", err)
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		path := filepath.Join(packsDir, entry.Name(), enrichmentFile)
		loaded, err := loadEnrichmentFile(path)
		if err != nil {
			return nil, err
		}
		for name, profile := range loaded {
			profiles[name] = profile
		}
	}
	return profiles, nil
}

// LoadEnrichmentProfile loads a single enrichment profile by encoder name from
// the default packs directory.
func LoadEnrichmentProfile(encoderName string) (EnrichmentProfile, error) {
	return LoadEnrichmentProfileFromPacks(encoderName, defaultPacksDir())
}

// LoadEnrichmentProfileFromPacks loads a single enrichment profile by encoder
// name from the given packs directory.
func LoadEnrichmentProfileFromPacks(encoderName, packsDir string) (EnrichmentProfile, error) {
	profiles, err := LoadEnrichmentProfiles(packsDir)
	if err != nil {
		return EnrichmentProfile{}, err
	}
	profile, ok := profiles[encoderName]
	if !ok {
		return EnrichmentProfile{}, fmt.Errorf("no enrichment profile for encoder: %s", encoderName)
	}
	return profile, nil
}

// LoadEnrichmentProfileForPlan loads a profile by encoder name, searching
// common pack locations relative to the compiled plan, then falling back to the
// default search paths.
func LoadEnrichmentProfileForPlan(encoderName, planDir string) (EnrichmentProfile, error) {
	// Plans may live at the project root (e.g. dist/security_lateral_movement)
	// or one level deeper. Try both relative paths.
	candidates := []string{
		filepath.Join(planDir, "..", "packs"),
		filepath.Join(planDir, "..", "..", "packs"),
	}
	for _, candidate := range candidates {
		if abs, err := filepath.Abs(candidate); err == nil {
			candidate = abs
		}
		if profile, err := LoadEnrichmentProfileFromPacks(encoderName, candidate); err == nil {
			return profile, nil
		}
	}
	return LoadEnrichmentProfile(encoderName)
}

func loadEnrichmentFile(path string) (map[string]EnrichmentProfile, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("read enrichment file %s: %w", path, err)
	}

	var raw struct {
		Profiles map[string]struct {
			Description string            `yaml:"description"`
			Defaults    map[string]any    `yaml:"defaults"`
			Mappings    map[string]string `yaml:"mappings"`
		} `yaml:"profiles"`
	}
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("parse enrichment file %s: %w", path, err)
	}

	profiles := make(map[string]EnrichmentProfile, len(raw.Profiles))
	for encoderName, p := range raw.Profiles {
		profiles[encoderName] = EnrichmentProfile{
			Encoder:     encoderName,
			Defaults:    p.Defaults,
			Mappings:    p.Mappings,
			Description: p.Description,
		}
	}
	return profiles, nil
}

func defaultPacksDir() string {
	// The runtime binary is typically run from the project root or a dist
	// directory. Try the repository packs layout first.
	if _, err := os.Stat("packs"); err == nil {
		return "packs"
	}
	// Fall back to a path relative to the module source.
	return filepath.Join("..", "..", "..", "packs")
}
