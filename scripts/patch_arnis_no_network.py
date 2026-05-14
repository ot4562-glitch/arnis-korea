#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "upstream" / "arnis" / "src" / "main.rs"


def replace_once(text: str, old: str, new: str, marker: str) -> str:
    if marker in text:
        return text
    if old not in text:
        raise SystemExit(f"patch anchor not found: {old[:80]!r}")
    return text.replace(old, new, 1)


def main() -> int:
    text = MAIN.read_text(encoding="utf-8")
    text = replace_once(
        text,
        """    // Check for updates
    if let Err(e) = version_check::check_for_updates() {
        eprintln!(
            "{}: {}",
            "Error checking for version updates".red().bold(),
            e
        );
    }

    // Parse input arguments
    let args: Args = Args::parse();
""",
        """    let arnis_korea_naver_only = env::var("ARNIS_KOREA_NAVER_ONLY").ok().as_deref() == Some("1");

    // Check for updates, except for the Arnis Korea no-network renderer path.
    if !arnis_korea_naver_only {
        if let Err(e) = version_check::check_for_updates() {
            eprintln!(
                "{}: {}",
                "Error checking for version updates".red().bold(),
                e
            );
        }
    }

    // Parse input arguments
    let args: Args = Args::parse();

    if arnis_korea_naver_only && args.file.is_none() {
        eprintln!(
            "{}: Arnis Korea Naver-only renderer requires --file and will not fetch external map data.",
            "Error".red().bold()
        );
        std::process::exit(1);
    }
""",
        "Arnis Korea Naver-only renderer requires --file",
    )
    text = replace_once(
        text,
        """    // Fetch supplementary building data from Overture Maps
    {
        println!("{} Fetching Overture Maps data...", "  [+]".bold());
        let overture_elements =
            overture::fetch_overture_buildings(&args.bbox, args.scale, args.debug);
        if !overture_elements.is_empty() {
            let before_count = parsed_elements.len();
            let unique_overture =
                overture::deduplicate_against_osm(overture_elements, &parsed_elements);
            parsed_elements.extend(unique_overture);
            let added = parsed_elements.len() - before_count;
            println!(
                "  Added {} buildings from Overture Maps",
                added.to_string().bright_white().bold()
            );
        } else {
            println!("  No additional buildings from Overture Maps for this area");
        }
    }
""",
        """    // Fetch supplementary building data from Overture Maps, except for
    // Arnis Korea Naver-only renderer mode where all external non-Naver
    // network sources are disabled and --file is the only map input.
    if !arnis_korea_naver_only {
        println!("{} Fetching Overture Maps data...", "  [+]".bold());
        let overture_elements =
            overture::fetch_overture_buildings(&args.bbox, args.scale, args.debug);
        if !overture_elements.is_empty() {
            let before_count = parsed_elements.len();
            let unique_overture =
                overture::deduplicate_against_osm(overture_elements, &parsed_elements);
            parsed_elements.extend(unique_overture);
            let added = parsed_elements.len() - before_count;
            println!(
                "  Added {} buildings from Overture Maps",
                added.to_string().bright_white().bold()
            );
        } else {
            println!("  No additional buildings from Overture Maps for this area");
        }
    } else {
        println!("{} Arnis Korea no-network renderer: Overture fetch disabled", "  [+]".bold());
    }
""",
        "Overture fetch disabled",
    )
    MAIN.write_text(text, encoding="utf-8")
    print(f"patched {MAIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
