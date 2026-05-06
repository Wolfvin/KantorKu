#!/usr/bin/env bash
# =====================================================
# KantorKu Skill Navigator — Skill Discovery & Routing
# Commands: list | find <query> | show <skill> | route <query>
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
SKILLS_DIR="${KANTORKU_DIR}/skills"
SKILL_MAP="${SKILLS_DIR}/skill-map.tsv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ─────────────────────────────────────
# list: Show all available skills
# ─────────────────────────────────────
cmd_list() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   KantorKu Skills                    ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
    echo ""

    if [[ -f "${SKILL_MAP}" ]]; then
        # Parse TSV header
        printf "%-15s %-18s %s\n" "SKILL" "CATEGORY" "KEYWORDS"
        printf "%-15s %-18s %s\n" "─────" "────────" "────────"
        tail -n +2 "${SKILL_MAP}" | while IFS=$'\t' read -r name category keywords; do
            printf "%-15s %-18s %s\n" "${name}" "${category}" "${keywords}"
        done
    else
        # Fallback: scan skill directories
        printf "%-15s %s\n" "SKILL" "DESCRIPTION"
        printf "%-15s %s\n" "─────" "───────────"
        for skill_dir in "${SKILLS_DIR}"/*/; do
            if [[ -d "${skill_dir}" ]]; then
                local skill_name
                skill_name="$(basename "${skill_dir}")"
                local skill_md="${skill_dir}SKILL.md"
                if [[ -f "${skill_md}" ]]; then
                    local purpose
                    purpose=$(sed -n 's/^## Purpose$//p' "${skill_md}" 2>/dev/null || echo "")
                    # Get first line after "## Purpose"
                    local desc
                    desc=$(awk '/^## Purpose/{getline; print; exit}' "${skill_md}" 2>/dev/null || echo "N/A")
                    printf "%-15s %s\n" "${skill_name}" "${desc}"
                else
                    printf "%-15s %s\n" "${skill_name}" "(no SKILL.md)"
                fi
            fi
        done
    fi

    echo ""
}

# ─────────────────────────────────────
# find: Search skills by keyword
# ─────────────────────────────────────
cmd_find() {
    local query="${1:-}"
    if [[ -z "${query}" ]]; then
        echo "Usage: skill-navigator.sh find <query>"
        exit 1
    fi

    echo ""
    echo -e "${CYAN}Searching for: '${query}'${NC}"
    echo ""

    local found=0

    if [[ -f "${SKILL_MAP}" ]]; then
        # Search in skill-map.tsv
        while IFS=$'\t' read -r name category keywords; do
            [[ "${name}" == "skill_name" ]] && continue  # skip header
            if echo "${name} ${category} ${keywords}" | grep -qi "${query}"; then
                echo -e "  ${GREEN}●${NC} ${name} (${category})"
                echo -e "    Keywords: ${keywords}"
                found=1
            fi
        done < "${SKILL_MAP}"
    fi

    # Also search in SKILL.md files
    for skill_dir in "${SKILLS_DIR}"/*/; do
        if [[ -d "${skill_dir}" ]]; then
            local skill_name
            skill_name="$(basename "${skill_dir}")"
            local skill_md="${skill_dir}SKILL.md"
            if [[ -f "${skill_md}" ]] && grep -qi "${query}" "${skill_md}"; then
                if [[ ${found} -eq 0 ]]; then
                    echo -e "  ${GREEN}●${NC} ${skill_name} (matched in SKILL.md)"
                    found=1
                fi
            fi
        fi
    done

    if [[ ${found} -eq 0 ]]; then
        echo -e "  ${YELLOW}No skills found matching '${query}'${NC}"
    fi
    echo ""
}

# ─────────────────────────────────────
# show: Display detailed skill info
# ─────────────────────────────────────
cmd_show() {
    local skill_name="${1:-}"
    if [[ -z "${skill_name}" ]]; then
        echo "Usage: skill-navigator.sh show <skill>"
        exit 1
    fi

    local skill_dir="${SKILLS_DIR}/${skill_name}"
    if [[ ! -d "${skill_dir}" ]]; then
        echo -e "${RED}Skill '${skill_name}' not found${NC}"
        exit 1
    fi

    echo ""
    echo -e "${CYAN}═══ ${skill_name} ═══${NC}"
    echo ""

    # Show SKILL.md
    if [[ -f "${skill_dir}/SKILL.md" ]]; then
        cat "${skill_dir}/SKILL.md"
    else
        echo "(No SKILL.md found)"
    fi

    # Show agent config
    if [[ -f "${skill_dir}/agents/openai.yaml" ]]; then
        echo ""
        echo -e "${CYAN}Agent Configuration:${NC}"
        cat "${skill_dir}/agents/openai.yaml"
    fi

    echo ""
}

# ─────────────────────────────────────
# route: Determine best skill for a query
# ─────────────────────────────────────
cmd_route() {
    local query="${1:-}"
    if [[ -z "${query}" ]]; then
        echo "Usage: skill-navigator.sh route <query>"
        exit 1
    fi

    echo ""
    echo -e "${CYAN}Routing query: '${query}'${NC}"
    echo ""

    local best_skill=""
    local best_score=0

    if [[ -f "${SKILL_MAP}" ]]; then
        while IFS=$'\t' read -r name category keywords; do
            [[ "${name}" == "skill_name" ]] && continue
            local score=0

            # Score based on keyword matches
            IFS=',' read -ra kws <<< "${keywords}"
            for kw in "${kws[@]}"; do
                kw="$(echo "${kw}" | xargs)"  # trim
                if echo "${query}" | grep -qi "${kw}"; then
                    ((score++))
                fi
            done

            if [[ ${score} -gt ${best_score} ]]; then
                best_score=${score}
                best_skill="${name}"
            fi
        done < "${SKILL_MAP}"
    fi

    if [[ -n "${best_skill}" ]] && [[ ${best_score} -gt 0 ]]; then
        echo -e "  ${GREEN}→ ${best_skill}${NC} (score: ${best_score})"
        echo ""
        echo -e "  ${BLUE}Tip:${NC} Run 'skill-navigator.sh show ${best_skill}' for details"
    else
        echo -e "  ${YELLOW}No matching skill found${NC}"
        echo ""
        echo "  Available skills:"
        cmd_list
    fi

    echo ""
}

# ─────────────────────────────────────
# Usage
# ─────────────────────────────────────
usage() {
    echo "Usage: skill-navigator.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  list              Show all available skills"
    echo "  find <query>      Search skills by keyword"
    echo "  show <skill>      Display detailed skill info"
    echo "  route <query>     Determine best skill for a query"
    echo ""
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
case "${1:-}" in
    list)   cmd_list ;;
    find)   cmd_find "${2:-}" ;;
    show)   cmd_show "${2:-}" ;;
    route)  cmd_route "${2:-}" ;;
    *)
        usage
        exit 1
        ;;
esac
