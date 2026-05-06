pub mod kantor;
pub mod library;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Mode {
    Kantor,
    Library,
}

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: Mode variants exist and are PartialEq
    #[test]
    fn test_mode_variants() {
        assert_eq!(Mode::Kantor, Mode::Kantor, "AI Agent: Kantor must equal Kantor");
        assert_eq!(Mode::Library, Mode::Library, "AI Agent: Library must equal Library");
        assert_ne!(Mode::Kantor, Mode::Library, "AI Agent: Kantor must not equal Library");
    }

    // AI Agent verifies: Mode implements Debug
    #[test]
    fn test_mode_debug() {
        let k = format!("{:?}", Mode::Kantor);
        let l = format!("{:?}", Mode::Library);
        assert!(k.contains("Kantor"), "AI Agent: Debug for Kantor must contain 'Kantor'");
        assert!(l.contains("Library"), "AI Agent: Debug for Library must contain 'Library'");
    }

    // AI Agent verifies: Mode implements Clone and Copy
    #[test]
    fn test_mode_clone_copy() {
        let a = Mode::Kantor;
        let b = a; // Copy
        let c = a; // Copy again
        assert_eq!(a, b, "AI Agent: Copy must produce equal value");
        assert_eq!(a, c, "AI Agent: Copy must produce equal value");

        let d = a.clone(); // Clone
        assert_eq!(a, d, "AI Agent: Clone must produce equal value");
    }
}
