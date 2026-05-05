pub mod kantor;
pub mod library;

#[derive(Debug, Clone, PartialEq)]
pub enum Mode {
    Kantor,
    Library,
}
