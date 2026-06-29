package encoder

import (
	"fmt"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// NginxAccess encodes events as nginx combined log format lines.
type NginxAccess struct{}

func init() {
	Register("nginx-access", NginxAccess{})
}

// Name returns the encoder name.
func (NginxAccess) Name() string { return "nginx-access" }

// ContentType returns the MIME type of the encoded output.
func (NginxAccess) ContentType() string { return "text/plain" }

// Encode formats the event as an nginx combined log line.
func (NginxAccess) Encode(ev event.Event) ([]byte, error) {
	required := []string{"remote_addr", "request", "status", "body_bytes_sent"}
	missing := make([]string, 0, len(required))
	for _, key := range required {
		if _, ok := ev.Attributes[key]; !ok {
			missing = append(missing, key)
		}
	}
	if len(missing) > 0 {
		return nil, NewEncodeError(fmt.Sprintf("missing required fields: %v", missing))
	}

	remoteAddr, _ := ev.Attributes["remote_addr"].(string)
	remoteUser := "-"
	if u, ok := ev.Attributes["remote_user"].(string); ok && u != "" {
		remoteUser = u
	}
	request, _ := ev.Attributes["request"].(string)
	status := fmt.Sprintf("%v", ev.Attributes["status"])
	bodyBytes := fmt.Sprintf("%v", ev.Attributes["body_bytes_sent"])
	timeLocal := ev.EventTime.Format("02/Jan/2006:15:04:05 -0700")
	referer := "-"
	if r, ok := ev.Attributes["http_referer"].(string); ok && r != "" {
		referer = r
	}
	userAgent := "-"
	if ua, ok := ev.Attributes["http_user_agent"].(string); ok && ua != "" {
		userAgent = ua
	}

	line := fmt.Sprintf(
		`%s - %s [%s] "%s" %s %s "%s" "%s"`,
		remoteAddr, remoteUser, timeLocal, request, status, bodyBytes, referer, userAgent,
	)
	return []byte(line), nil
}
