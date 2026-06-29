package kafka

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	segmentio "github.com/segmentio/kafka-go"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// MessageWriter is the subset of segmentio/kafka-go.Writer used by the sink.
type MessageWriter interface {
	WriteMessages(ctx context.Context, msgs ...segmentio.Message) error
	Close() error
}

// Sink writes events to Kafka.
type Sink struct {
	writer  MessageWriter
	keyFunc func(event.Event) []byte
	timeout time.Duration
	retries int
	count   int
	failed  int
	enc     encoder.Encoder
}

// New creates a Kafka sink with a real writer.
func New(brokers string, topic string, keyField string, timeout time.Duration, retries int, enc ...encoder.Encoder) *Sink {
	return newSink(
		segmentio.NewWriter(segmentio.WriterConfig{
			Brokers: strings.Split(brokers, ","),
			Topic:   topic,
			Async:   false,
		}),
		KeyFunc(keyField),
		timeout,
		retries,
		enc...,
	)
}

func newSink(writer MessageWriter, keyFunc func(event.Event) []byte, timeout time.Duration, retries int, enc ...encoder.Encoder) *Sink {
	s := &Sink{
		writer:  writer,
		keyFunc: keyFunc,
		timeout: timeout,
		retries: retries,
	}
	if len(enc) > 0 {
		s.enc = enc[0]
	}
	return s
}

// Open initializes the sink.
func (s *Sink) Open() error { return nil }

// Write sends one event to Kafka.
func (s *Sink) Write(ev event.Event) error {
	var body []byte
	var err error
	if s.enc != nil {
		body, err = s.enc.Encode(ev)
	} else {
		body, err = json.Marshal(ev)
	}
	if err != nil {
		s.failed++
		return err
	}

	msg := segmentio.Message{
		Key:   s.keyFunc(ev),
		Value: body,
		Time:  time.Now(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), s.timeout)
	defer cancel()

	attempt := 0
	for {
		err := s.writer.WriteMessages(ctx, msg)
		if err == nil {
			s.count++
			return nil
		}
		if attempt < s.retries {
			attempt++
			continue
		}
		s.failed++
		return err
	}
}

// Flush is a no-op.
func (s *Sink) Flush() error { return nil }

// Close closes the Kafka writer.
func (s *Sink) Close() error { return s.writer.Close() }

// Count returns successful writes.
func (s *Sink) Count() int { return s.count }

// Failed returns failed writes.
func (s *Sink) Failed() int { return s.failed }

func KeyFunc(field string) func(event.Event) []byte {
	switch field {
	case "event_id":
		return func(ev event.Event) []byte { return []byte(ev.EventID) }
	case "flow_id":
		return func(ev event.Event) []byte {
			if ev.FlowID != nil {
				return []byte(*ev.FlowID)
			}
			return nil
		}
	case "source_id":
		return func(ev event.Event) []byte { return []byte(ev.SourceID) }
	case "":
		return func(ev event.Event) []byte { return nil }
	default:
		return func(ev event.Event) []byte { return []byte(ev.EventID) }
	}
}

// ValidateConfig checks required kafka parameters.
func ValidateConfig(brokers, topic string) error {
	if brokers == "" {
		return fmt.Errorf("--brokers is required for kafka sink")
	}
	if topic == "" {
		return fmt.Errorf("--topic is required for kafka sink")
	}
	return nil
}
