package security

import (
	"fmt"
	"strconv"

	"github.com/linxinhong/eventweave/runtime-go/internal/encoder"
	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// require checks that all keys exist in event attributes. Returns an error
// listing missing fields if any are absent.
func require(ev event.Event, keys []string) error {
	missing := make([]string, 0, len(keys))
	for _, key := range keys {
		if _, ok := ev.Attributes[key]; !ok {
			missing = append(missing, key)
		}
	}
	if len(missing) > 0 {
		return encoder.NewEncodeError(fmt.Sprintf("missing required fields: %v", missing))
	}
	return nil
}

// attr retrieves an attribute value or a default when missing.
func attr(ev event.Event, key string, def any) any {
	if value, ok := ev.Attributes[key]; ok {
		return value
	}
	return def
}

// asString returns the string representation of an attribute value.
func asString(value any) string {
	switch v := value.(type) {
	case string:
		return v
	case int:
		return strconv.Itoa(v)
	case int64:
		return strconv.FormatInt(v, 10)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	case bool:
		return strconv.FormatBool(v)
	default:
		return fmt.Sprintf("%v", v)
	}
}
