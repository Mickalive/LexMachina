from app.section_modes import SectionModeLoader
from pathlib import Path

# Use the same path construction as the test
section_dir = Path(__file__).parent.parent / 'results' / 'fractal_map' / 'section_scaled'
fallback_dir = Path(__file__).parent.parent / 'results' / 'fractal_map' / 'section_experiment_clean'

print(f'section_dir: {section_dir}')
print(f'section_dir exists: {section_dir.exists()}')
print(f'section_scaled_v2: {section_dir.parent / "section_scaled_v2"}')
print(f'section_scaled_v2 exists: {(section_dir.parent / "section_scaled_v2").exists()}')

loader = SectionModeLoader(str(section_dir), str(fallback_dir))
print(f'primary_dirs: {loader.primary_dirs}')
count = loader.load()
print(f'Loaded {count} section modes')
print(f'active_dir: {loader.active_dir}')
print(f'_is_scaled: {loader._is_scaled}')
print(f'_source_label: {loader._source_label}')

for mode_name in ['sachverhalt', 'erwaegungen', 'dispositiv', 'full_text', 'erwaegungen_dispositiv', 'sachverhalt_erwaegungen_dispositiv']:
    mode = loader.get_mode(mode_name)
    if mode:
        print(f'  {mode_name}: {mode.n_decisions} total, {mode.n_section_decisions} section, {mode.n_baseline_decisions} baseline')
