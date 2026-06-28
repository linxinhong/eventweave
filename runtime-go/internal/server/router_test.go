package server

import (
	"testing"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

func TestSourceFilterMatchSourceID(t *testing.T) {
	f := SourceFilter{SourceID: "edr-001"}
	if !f.Match(event.Event{SourceID: "edr-001", EventType: "user.login"}) {
		t.Fatal("expected match")
	}
	if f.Match(event.Event{SourceID: "firewall-001", EventType: "user.login"}) {
		t.Fatal("expected no match")
	}
}

func TestSourceFilterMatchEventType(t *testing.T) {
	f := SourceFilter{EventType: "user.login"}
	if !f.Match(event.Event{SourceID: "edr-001", EventType: "user.login"}) {
		t.Fatal("expected match")
	}
	if f.Match(event.Event{SourceID: "edr-001", EventType: "network.connection"}) {
		t.Fatal("expected no match")
	}
}

func TestSourceFilterMatchCombined(t *testing.T) {
	f := SourceFilter{SourceID: "edr-001", EventType: "user.login"}
	if !f.Match(event.Event{SourceID: "edr-001", EventType: "user.login"}) {
		t.Fatal("expected match")
	}
	if f.Match(event.Event{SourceID: "edr-001", EventType: "network.connection"}) {
		t.Fatal("expected no match")
	}
	if f.Match(event.Event{SourceID: "firewall-001", EventType: "user.login"}) {
		t.Fatal("expected no match")
	}
}

func TestSourceFilterEmptyMatchesAll(t *testing.T) {
	f := SourceFilter{}
	if !f.Match(event.Event{SourceID: "anything", EventType: "anything"}) {
		t.Fatal("empty filter should match all")
	}
}
