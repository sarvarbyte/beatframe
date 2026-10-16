import os
import typer
from pathlib import Path

from beatframe.schema import load_project
from beatframe.web import stats

def run_audit(project_path: Path):
    # 1. Loyihani va fayllarni o'qib olish
    p = load_project(project_path)
    out_dir = project_path.parent / "output"
    srt_file = out_dir / "subtitles.srt"
    
    if not srt_file.exists():
        typer.echo(f"✗ Subtitr topilmadi: {srt_file}. Avval videoni 'make' qiling.")
        raise typer.Exit(1)
        
    subtitles = srt_file.read_text(encoding="utf-8")
    
    # 2. YouTube statistikasini sizning web/stats.py funksiyangizdan to'g'ridan-to'g'ri olish
    typer.echo("📊 YouTube statistikasi tortib olinmoqda...")
    try:
        channel_stats = stats.build_report(days=28)
    except Exception as e:
        typer.echo(f"✗ Statistika olishda xatolik: {e}. 'Studio'da YouTube'ga ulanganingizni tekshiring.")
        raise typer.Exit(1)

    # 3. Gemini API ga ulanish (Kalitni kompyuter muhitidan olamiz)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        typer.echo("✗ GEMINI_API_KEY topilmadi. Terminalda 'export GEMINI_API_KEY=kalitingiz' qilib bering.")
        raise typer.Exit(1)
        
    try:
        from google import genai
    except ImportError:
        typer.echo("✗ Gemini kutubxonasi o'rnatilmagan. Bir marta: .venv/bin/pip install -e '.[audit]'")
        raise typer.Exit(1)
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Sen Human Unknowns kanalining bosh prodyuserisan.
    Kanal statistikasi:
    {channel_stats}
    
    Tahlil qilinayotgan video: {p.title}
    Ssenariysi (subtitles):
    {subtitles}
    
    Vazifang:
    1. Ssenariydagi "hook" (boshlanish) qismi auditoriyani ushlab qola oladimi?
    2. Statistikaga qarab (retention % va views), bu videoning muammosi nimada ekanini top.
    3. Keyingi shunday video uchun 3 ta aniq amaliy maslahat ber.
    Javobni qisqa, Markdown formatida, o'zbek tilida qaytar.
    """
    
    typer.echo(f"🤖 '{p.title}' Gemini tomonidan tahlil qilinmoqda, kuting...\n")
    response = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
    
    # Natijani terminalga chiqarish va faylga saqlash
    report_file = out_dir / "ai_audit_report.md"
    report_file.write_text(response.text, encoding="utf-8")
    
    typer.echo(response.text)
    typer.echo(f"\n✓ Tahlil saqlandi: {report_file}")