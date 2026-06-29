package security

import (
	"fmt"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// ZeekConn encodes events as Zeek conn.log TSV entries.
type ZeekConn struct{}

func init() {
	encoder.Register("zeek-conn", ZeekConn{})
}

// Name returns the encoder name.
func (ZeekConn) Name() string { return "zeek-conn" }

// ContentType returns the MIME type of the encoded output.
func (ZeekConn) ContentType() string { return "text/tab-separated-values" }

// Encode formats the event as a Zeek conn.log tab-separated line.
func (ZeekConn) Encode(ev event.Event) ([]byte, error) {
	if err := require(ev, []string{"uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "proto"}); err != nil {
		return nil, err
	}
	line := fmt.Sprintf(
		"%s\t%s\t%s\t%s\t%s\t%s\t%s",
		asString(attr(ev, "ts", ev.EventTime.Format("2006-01-02T15:04:05.000000Z"))),
		asString(ev.Attributes["uid"]),
		asString(ev.Attributes["id.orig_h"]),
		asString(ev.Attributes["id.orig_p"]),
		asString(ev.Attributes["id.resp_h"]),
		asString(ev.Attributes["id.resp_p"]),
		asString(ev.Attributes["proto"]),
	)
	return []byte(line), nil
}

// ZeekDNS encodes events as Zeek dns.log TSV entries.
type ZeekDNS struct{}

func init() {
	encoder.Register("zeek-dns", ZeekDNS{})
}

// Name returns the encoder name.
func (ZeekDNS) Name() string { return "zeek-dns" }

// ContentType returns the MIME type of the encoded output.
func (ZeekDNS) ContentType() string { return "text/tab-separated-values" }

// Encode formats the event as a Zeek dns.log tab-separated line.
func (ZeekDNS) Encode(ev event.Event) ([]byte, error) {
	if err := require(ev, []string{"uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "query"}); err != nil {
		return nil, err
	}
	line := fmt.Sprintf(
		"%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s",
		asString(attr(ev, "ts", ev.EventTime.Format("2006-01-02T15:04:05.000000Z"))),
		asString(ev.Attributes["uid"]),
		asString(ev.Attributes["id.orig_h"]),
		asString(ev.Attributes["id.orig_p"]),
		asString(ev.Attributes["id.resp_h"]),
		asString(ev.Attributes["id.resp_p"]),
		asString(ev.Attributes["query"]),
		asString(attr(ev, "qtype_name", "")),
	)
	return []byte(line), nil
}
