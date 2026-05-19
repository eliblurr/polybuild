// Package greeting is a trivial shared library. Its only purpose is to give
// the build graph a cross-package edge: //services/greeter depends on it, so
// the two targets exercise Bazel's incremental + cached rebuild behavior.
package greeting

import "fmt"

// Greet returns a greeting for name.
func Greet(name string) string {
	return fmt.Sprintf("Hello, %s — from polybuild.", name)
}
