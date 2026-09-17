#!/usr/bin/env bash

say_hello() {
  echo "hello from the sample project"
}

main() {
  say_hello
}

main "$@"
