import subprocess
import sys
import time
from typing import Tuple

JOBS = [
    "clean_product_item.py",
    "clean_family.py",
    "clean_geographical_area.py",
    "clean_document_status.py",
    "clean_document_type.py",
    "clean_item.py",
    "clean_tiers.py",
    "clean_warehouse.py",
    "clean_document.py",
    "clean_document_line.py",
]


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def run_job(job: str) -> Tuple[bool, float]:
    print(f"\n{'='*50}")
    print(f"🚀 Lancement : {job}")
    print(f"{'='*50}")

    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, f"/opt/jobs/{job}"],
        capture_output=False
    )
    duration = time.perf_counter() - start

    if result.returncode != 0:
        print(f"❌ Échec : {job}  ⏱ {format_duration(duration)}")
        return False, duration

    print(f"✅ Succès : {job}  ⏱ {format_duration(duration)}")
    return True, duration


if __name__ == "__main__":
    failed   = []
    timings  = {}
    total_start = time.perf_counter()

    for job in JOBS:
        success, duration = run_job(job)
        timings[job] = duration
        if not success:
            failed.append(job)

    total_duration = time.perf_counter() - total_start

    print(f"\n{'='*50}")
    print(f"⏱  Temps d'exécution par job :")
    print(f"{'─'*50}")
    for job, duration in timings.items():
        status = "✅" if job not in failed else "❌"
        print(f"  {status}  {job:<35} {format_duration(duration):>8}")
    print(f"{'─'*50}")
    print(f"  🕒  Total                                {format_duration(total_duration):>8}")
    print(f"{'='*50}")
    print(f"📊 Résumé : {len(JOBS) - len(failed)}/{len(JOBS)} jobs réussis")
    if failed:
        print(f"❌ Jobs échoués : {failed}")
    else:
        print("🏁 Tous les jobs terminés avec succès ✅")