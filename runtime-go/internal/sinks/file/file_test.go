package file

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestFileSinkWritesJSONL(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "events.jsonl")
	sink := New(path, dir)
	if err := sink.Open(); err != nil {
		t.Fatalf("open: %v", err)
	}

	for _, id := range []string{"e1", "e2"} {
		ev := event.Event{EventID: id, EventTime: time.Now()}
		if err := sink.Write(ev); err != nil {
			t.Fatalf("write: %v", err)
		}
	}
	if err := sink.Close(); err != nil {
		t.Fatalf("close: %v", err)
	}

	file, err := os.Open(path)
	if err != nil {
		t.Fatalf("open result: %v", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	var ids []string
	for scanner.Scan() {
		var ev event.Event
		if err := json.Unmarshal(scanner.Bytes(), &ev); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}
		ids = append(ids, ev.EventID)
	}
	if len(ids) != 2 || ids[0] != "e1" || ids[1] != "e2" {
		t.Fatalf("unexpected ids: %+v", ids)
	}
}

func TestFileSinkRejectsTraversal(t *testing.T) {
	dir := t.TempDir()
	sink := New("../etc/passwd", dir)
	if err := sink.Open(); err == nil {
		t.Fatal("expected error for path traversal")
	}
}

func TestFileSinkRejectsAbsoluteOutsideOutputDir(t *testing.T) {
	dir := t.TempDir()
	sink := New("/etc/passwd", dir)
	if err := sink.Open(); err == nil {
		t.Fatal("expected error for absolute path outside output directory")
	}
}
