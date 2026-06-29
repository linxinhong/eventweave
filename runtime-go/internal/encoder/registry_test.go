package encoder

import "testing"

func TestListIncludesBuiltInEncoders(t *testing.T) {
	names := List()
	want := map[string]bool{
		"jsonl":          false,
		"syslog-rfc3164": false,
		"syslog-rfc5424": false,
		"nginx-access":   false,
	}
	for _, name := range names {
		if _, ok := want[name]; ok {
			want[name] = true
		}
	}
	for name, found := range want {
		if !found {
			t.Errorf("encoder %q not registered", name)
		}
	}
}

func TestGetUnknownEncoder(t *testing.T) {
	if _, err := Get("no-such-encoder"); err == nil {
		t.Fatal("expected error for unknown encoder")
	}
}
