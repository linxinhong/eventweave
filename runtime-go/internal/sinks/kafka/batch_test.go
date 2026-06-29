package kafka

import (
	"context"
	"errors"
	"testing"
	"time"

	segmentio "github.com/segmentio/kafka-go"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

type batchFakeWriter struct {
	batches [][]segmentio.Message
	fail    bool
}

func (w *batchFakeWriter) WriteMessages(ctx context.Context, msgs ...segmentio.Message) error {
	if w.fail {
		return errors.New("write failed")
	}
	batch := make([]segmentio.Message, len(msgs))
	copy(batch, msgs)
	w.batches = append(w.batches, batch)
	return nil
}

func (w *batchFakeWriter) Close() error { return nil }

func TestBatchSinkFlushesOnSize(t *testing.T) {
	w := &batchFakeWriter{}
	s := NewBatch(w, KeyFunc(""), 3, 1*time.Second, 5*time.Second, 0)

	for i := 0; i < 7; i++ {
		if err := s.Write(event.Event{EventID: string(rune('a' + i))}); err != nil {
			t.Fatalf("write: %v", err)
		}
	}
	_ = s.Flush()
	_ = s.Close()

	if len(w.batches) != 3 {
		t.Fatalf("expected 3 batches, got %d", len(w.batches))
	}
	if len(w.batches[0]) != 3 || len(w.batches[1]) != 3 || len(w.batches[2]) != 1 {
		sizes := []int{len(w.batches[0]), len(w.batches[1]), len(w.batches[2])}
		t.Fatalf("unexpected batch sizes: %v", sizes)
	}
	if s.Count() != 7 {
		t.Fatalf("expected count 7, got %d", s.Count())
	}
}

func TestBatchSinkFlushesOnTimeout(t *testing.T) {
	w := &batchFakeWriter{}
	s := NewBatch(w, KeyFunc(""), 100, 50*time.Millisecond, 5*time.Second, 0)

	if err := s.Write(event.Event{EventID: "a"}); err != nil {
		t.Fatalf("write: %v", err)
	}

	time.Sleep(150 * time.Millisecond)
	_ = s.Close()

	if len(w.batches) != 1 {
		t.Fatalf("expected 1 timed flush, got %d", len(w.batches))
	}
	if len(w.batches[0]) != 1 {
		t.Fatalf("expected batch size 1, got %d", len(w.batches[0]))
	}
}

func TestBatchSinkCountsFailures(t *testing.T) {
	w := &batchFakeWriter{fail: true}
	s := NewBatch(w, KeyFunc(""), 2, 1*time.Second, 5*time.Second, 0)

	for i := 0; i < 4; i++ {
		_ = s.Write(event.Event{EventID: string(rune('a' + i))})
	}
	_ = s.Flush()
	_ = s.Close()

	if s.Failed() != 4 {
		t.Fatalf("expected 4 failed, got %d", s.Failed())
	}
}
