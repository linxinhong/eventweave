package kafka

import (
	"context"
	"encoding/json"
	"errors"
	"sync"
	"time"

	segmentio "github.com/segmentio/kafka-go"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
	"github.com/linxinhong/eventweave/runtime-go/internal/metrics"
)

// BatchSink buffers events and writes them to Kafka in batches.
type BatchSink struct {
	writer  MessageWriter
	keyFunc func(event.Event) []byte
	batchSize    int
	batchTimeout time.Duration
	timeout      time.Duration
	retries      int
	mode         string

	mu     sync.Mutex
	buffer []segmentio.Message
	count  int
	failed int
	closed bool
	done   chan struct{}
	timer  *time.Timer
}

// NewBatch creates a batching Kafka sink.
func NewBatch(writer MessageWriter, keyFunc func(event.Event) []byte, batchSize int, batchTimeout, timeout time.Duration, retries int) *BatchSink {
	return NewBatchWithMode(writer, keyFunc, batchSize, batchTimeout, timeout, retries, "run")
}

// NewBatchWithMode creates a batching Kafka sink with a mode label for metrics.
func NewBatchWithMode(writer MessageWriter, keyFunc func(event.Event) []byte, batchSize int, batchTimeout, timeout time.Duration, retries int, mode string) *BatchSink {
	metrics.RecordBatch(mode, "kafka", "success", 0)
	return &BatchSink{
		writer:       writer,
		keyFunc:      keyFunc,
		batchSize:    batchSize,
		batchTimeout: batchTimeout,
		timeout:      timeout,
		retries:      retries,
		mode:         mode,
		done:         make(chan struct{}),
	}
}

// Open initializes the batch sink.
func (s *BatchSink) Open() error { return nil }

// Write buffers an event and flushes when the batch is full.
func (s *BatchSink) Write(ev event.Event) error {
	body, err := json.Marshal(ev)
	if err != nil {
		s.failed++
		return err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if s.closed {
		return errors.New("kafka batch sink is closed")
	}

	s.buffer = append(s.buffer, segmentio.Message{
		Key:   s.keyFunc(ev),
		Value: body,
		Time:  time.Now(),
	})

	if len(s.buffer) >= s.batchSize {
		return s.flushLocked()
	}

	if s.timer == nil {
		s.timer = time.AfterFunc(s.batchTimeout, func() {
			s.mu.Lock()
			defer s.mu.Unlock()
			if s.closed {
				return
			}
			_ = s.flushLocked()
		})
	}
	return nil
}

// Flush sends any remaining buffered messages.
func (s *BatchSink) Flush() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.flushLocked()
}

// Close stops the timeout timer and flushes remaining messages.
func (s *BatchSink) Close() error {
	s.mu.Lock()
	if s.timer != nil {
		s.timer.Stop()
		s.timer = nil
	}
	s.closed = true
	_ = s.flushLocked()
	s.mu.Unlock()
	close(s.done)
	return s.writer.Close()
}

// Count returns successful writes.
func (s *BatchSink) Count() int { return s.count }

// Failed returns failed writes.
func (s *BatchSink) Failed() int { return s.failed }

// BatchSize returns the configured batch size.
func (s *BatchSink) BatchSize() int { return s.batchSize }

func (s *BatchSink) flushLocked() error {
	if len(s.buffer) == 0 {
		return nil
	}

	if s.timer != nil {
		s.timer.Stop()
		s.timer = nil
	}

	msgs := make([]segmentio.Message, len(s.buffer))
	copy(msgs, s.buffer)
	s.buffer = s.buffer[:0]
	batchLen := len(msgs)

	ctx, cancel := context.WithTimeout(context.Background(), s.timeout)
	defer cancel()

	attempt := 0
	for {
		err := s.writer.WriteMessages(ctx, msgs...)
		if err == nil {
			s.count += batchLen
			metrics.RecordBatch(s.mode, "kafka", "success", batchLen)
			return nil
		}
		if attempt < s.retries {
			attempt++
			continue
		}
		s.failed += batchLen
		metrics.RecordBatch(s.mode, "kafka", "failed", batchLen)
		return err
	}
}
