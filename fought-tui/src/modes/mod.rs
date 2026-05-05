pub mod kantor;
pub mod library;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Mode {
    Kantor,
    Library,
}
