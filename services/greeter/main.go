// greeter is a Go service. It is intentionally tiny — this repo demonstrates
// Bazel build engineering, not application code.
package main

import (
	"fmt"

	"github.com/elvissegbawu/polybuild/libs/go/greeting"
)

func main() {
	fmt.Println(greeting.Greet("world"))
}
