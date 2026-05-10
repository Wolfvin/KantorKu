pub mod office;
pub mod library;
pub mod symbolic;
pub mod losion;
pub mod gpu;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    Office,
    Library,
    Symbolic,
    Losion,
    Gpu,
}

#[cfg(test)]
mod tests {
    use super::*;

    // AI Agent verifies: Mode variants exist and are PartialEq
    #[test]
    fn test_mode_variants() {
        assert_eq!(Mode::Office, Mode::Office, "AI Agent: Office must equal Office");
        assert_eq!(Mode::Library, Mode::Library, "AI Agent: Library must equal Library");
        assert_eq!(Mode::Symbolic, Mode::Symbolic, "AI Agent: Symbolic must equal Symbolic");
        assert_eq!(Mode::Losion, Mode::Losion, "AI Agent: Losion must equal Losion");
        assert_eq!(Mode::Gpu, Mode::Gpu, "AI Agent: Gpu must equal Gpu");
        assert_ne!(Mode::Office, Mode::Library, "AI Agent: Office must not equal Library");
    }

    // AI Agent verifies: Mode implements Debug
    #[test]
    fn test_mode_debug() {
        let k = format!("{:?}", Mode::Office);
        let l = format!("{:?}", Mode::Library);
        let s = format!("{:?}", Mode::Symbolic);
        let lo = format!("{:?}", Mode::Losion);
        let g = format!("{:?}", Mode::Gpu);
        assert!(k.contains("Office"), "AI Agent: Debug for Office must contain 'Office'");
        assert!(l.contains("Library"), "AI Agent: Debug for Library must contain 'Library'");
        assert!(s.contains("Symbolic"), "AI Agent: Debug for Symbolic must contain 'Symbolic'");
        assert!(lo.contains("Losion"), "AI Agent: Debug for Losion must contain 'Losion'");
        assert!(g.contains("Gpu"), "AI Agent: Debug for Gpu must contain 'Gpu'");
    }

    // AI Agent verifies: Mode implements Clone and Copy
    #[test]
    fn test_mode_clone_copy() {
        let a = Mode::Office;
        let b = a; // Copy
        let c = a; // Copy again
        assert_eq!(a, b, "AI Agent: Copy must produce equal value");
        assert_eq!(a, c, "AI Agent: Copy must produce equal value");

        let d = a.clone(); // Clone
        assert_eq!(a, d, "AI Agent: Clone must produce equal value");
    }
}
