package kafka

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	segmentio "github.com/segmentio/kafka-go"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

type fakeWriter struct {
	messages []segmentio.Message
	fail     bool
}

func (f *fakeWriter) WriteMessages(ctx context.Context, msgs ...segmentio.Message) error {
	if f.fail {
		return errors.New("kafka unavailable")
	}
	f.messages = append(f.messages, msgs...)
	return nil
}

func (f *fakeWriter) Close() error { return nil }

func eventWithID(id string) event.Event {
	flow := "flow-1"
	return event.Event{
		EventID:    id,
		ScenarioID: "sc1",
		SourceID:   "src1",
		EventType:  "login",
		FlowID:     &flow,
		EventTime:  time.Now(),
	}
}

func TestKafkaSinkWritesEvent(t *testing.T) {
	fw := &fakeWriter{}
	sink := newSink(fw, KeyFunc(""), 5*time.Second, 0)
	ev := eventWithID("e1")
	if err := sink.Write(ev); err != nil {
		t.Fatalf("write: %v", err)
	}
	if sink.Count() != 1 || sink.Failed() != 0 {
		t.Fatalf("unexpected counts: count=%d failed=%d", sink.Count(), sink.Failed())
	}
	if len(fw.messages) != 1 {
		t.Fatalf("expected 1 message, got %d", len(fw.messages))
	}
	var decoded event.Event
	if err := json.Unmarshal(fw.messages[0].Value, &decoded); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if decoded.EventID != "e1" {
		t.Fatalf("unexpected event id: %s", decoded.EventID)
	}
}

func TestKafkaSinkCountsFailure(t *testing.T) {
	fw := &fakeWriter{fail: true}
	sink := newSink(fw, KeyFunc(""), 5*time.Second, 0)
	if err := sink.Write(eventWithID("e1")); err == nil {
		t.Fatal("expected error")
	}
	if sink.Count() != 0 || sink.Failed() != 1 {
		t.Fatalf("unexpected counts: count=%d failed=%d", sink.Count(), sink.Failed())
	}
}

func TestKafkaKeyEventID(t *testing.T) {
	fw := &fakeWriter{}
	sink := newSink(fw, KeyFunc("event_id"), 5*time.Second, 0)
	if err := sink.Write(eventWithID("e1")); err != nil {
		t.Fatalf("write: %v", err)
	}
	if string(fw.messages[0].Key) != "e1" {
		t.Fatalf("unexpected key: %s", string(fw.messages[0].Key))
	}
}

func TestKafkaKeyFlowID(t *testing.T) {
	fw := &fakeWriter{}
	sink := newSink(fw, KeyFunc("flow_id"), 5*time.Second, 0)
	if err := sink.Write(eventWithID("e1")); err != nil {
		t.Fatalf("write: %v", err)
	}
	if string(fw.messages[0].Key) != "flow-1" {
		t.Fatalf("unexpected key: %s", string(fw.messages[0].Key))
	}
}

func TestKafkaRequiresBrokersAndTopic(t *testing.T) {
	if err := ValidateConfig("", "topic"); err == nil {
		t.Fatal("expected error for missing brokers")
	}
	if err := ValidateConfig("127.0.0.1:9092", ""); err == nil {
		t.Fatal("expected error for missing topic")
	}
	if err := ValidateConfig("127.0.0.1:9092", "topic"); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}
