// echo is a second Go service. Two Go services + one Python service give the
// monorepo a small but genuinely polyglot build graph.
package main

import (
	"fmt"
	"os"
	"strings"
)

func main() {
	fmt.Println(strings.Join(os.Args[1:], " "))
}
