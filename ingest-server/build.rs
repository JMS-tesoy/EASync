fn main() {
    prost_build::compile_protos(&["../signal.proto"], &["../"]).unwrap();
}
