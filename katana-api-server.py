#!/usr/bin/env python3
"""
API Server para integração do katana-custom com ICMS
Hospedado em instância AWS EC2
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os
import asyncio
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Katana-Custom API", version="1.0.0")

# CORS para permitir requests do ICMS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações
KATANA_BINARY = "/app/katana"
SCRAPY_SCRIPT = "/app/scrapy-runner.py"
DATA_DIR = "/app/data"
CONFIG_DIR = "/app/config"
CACHE_EXPIRY_HOURS = 6  # Cache válido por 6 horas

@app.get("/")
async def root():
    return {"status": "Katana-Custom API Running", "timestamp": datetime.now()}

@app.get("/health")
async def health_check():
    """Health check para balanceadores e monitors em AWS"""
    try:
        # Verificar se katana está funcionando
        result = subprocess.run([KATANA_BINARY, "--version"], 
                              capture_output=True, text=True, timeout=5)
        katana_ok = result.returncode == 0
        
        return {
            "status": "healthy" if katana_ok else "unhealthy",
            "katana": katana_ok,
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/api/refresh/{category}")
async def refresh_category_data(category: str):
    """Força refresh dos dados de uma categoria"""
    try:
        logger.info(f"Manual refresh requested for category: {category}")
        
        # Executar análise completa
        urls = await run_katana_analysis(category)
        seo_data = await run_scrapy_analysis(urls, category)
        
        # Salvar timestamp do cache
        cache_file = f"{DATA_DIR}/{category}_cache.json"
        cache_data = {
            "category": category,
            "last_updated": datetime.now().isoformat(),
            "urls_count": len(urls),
            "pages_analyzed": len(seo_data.get("pages", []))
        }
        
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        
        return {
            "status": "success",
            "category": category,
            "urls_collected": len(urls),
            "pages_analyzed": len(seo_data.get("pages", [])),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing category {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/category-insights/{category}")
async def get_category_insights(category: str, background_tasks: BackgroundTasks):
    """
    Endpoint principal para análise de categoria
    Usado pelo ICMS Content Optimizer
    """
    try:
        logger.info(f"Analyzing category: {category}")
        
        # Verificar cache existente
        cache_file = f"{DATA_DIR}/{category}_cache.json"
        seo_file = f"{DATA_DIR}/{category}_seo.json"
        
        # Verificar se cache é válido (menos de 6 horas)
        use_cache = False
        if os.path.exists(cache_file) and os.path.exists(seo_file):
            try:
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)
                
                last_update = datetime.fromisoformat(cache_data["last_updated"])
                hours_diff = (datetime.now() - last_update).total_seconds() / 3600
                
                if hours_diff < CACHE_EXPIRY_HOURS:
                    use_cache = True
                    logger.info(f"Using cached data for {category} (updated {hours_diff:.1f}h ago)")
            except Exception as cache_error:
                logger.warning(f"Cache validation failed: {cache_error}")
        
        if use_cache:
            # Usar dados em cache
            try:
                with open(seo_file, "r") as f:
                    seo_data = json.load(f)
            except Exception as read_error:
                logger.error(f"Error reading cached data: {read_error}")
                seo_data = {"pages": []}
        else:
            # Executar análise completa em background se cache expirou
            if os.path.exists(seo_file):
                # Usar dados existentes enquanto atualiza em background
                try:
                    with open(seo_file, "r") as f:
                        seo_data = json.load(f)
                    
                    # Agendar refresh em background
                    background_tasks.add_task(refresh_category_background, category)
                    logger.info(f"Serving cached data and refreshing {category} in background")
                except Exception:
                    seo_data = {"pages": []}
            else:
                # Primeira vez - executar análise completa
                logger.info(f"First time analysis for {category}")
                urls = await run_katana_analysis(category)
                seo_data = await run_scrapy_analysis(urls, category)
                
                # Salvar cache
                cache_data = {
                    "category": category,
                    "last_updated": datetime.now().isoformat(),
                    "urls_count": len(urls),
                    "pages_analyzed": len(seo_data.get("pages", []))
                }
                
                with open(cache_file, "w") as f:
                    json.dump(cache_data, f)
        
        # Processar e retornar insights
        insights = process_category_insights(seo_data, category)
        
        return insights
        
    except Exception as e:
        logger.error(f"Error analyzing category {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_katana_analysis(category: str) -> list:
    """Executar katana usando lista curada de URLs da categoria"""
    try:
        # Verificar se existe lista de URLs para a categoria
        urls_list_file = f"{CONFIG_DIR}/{category}.txt"
        if not os.path.exists(urls_list_file):
            logger.warning(f"URL list not found for {category}, creating default")
            await create_default_url_list(category)
        
        # Comando katana com lista de URLs e JSONL
        cmd = [
            KATANA_BINARY,
            "-list", urls_list_file,
            "-jsonl",
            "-d", "1",      # profundidade
            "-c", "5",      # antes era 10
            "-headless",
            "-o", f"{DATA_DIR}/{category}.jsonl"
        ]
        
        logger.info(f"Running katana for {category}: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Katana failed: {stderr.decode()}")
        
        # Ler URLs coletadas do JSONL
        urls = []
        jsonl_file = f"{DATA_DIR}/{category}.jsonl"
        if os.path.exists(jsonl_file):
            with open(jsonl_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            url = item.get("url", "")
                            if url:
                                urls.append(url)
                        except json.JSONDecodeError:
                            continue
        
        logger.info(f"Katana collected {len(urls)} URLs for {category}")
        return urls[:30]  # Limite de 30 URLs
        
    except Exception as e:
        logger.error(f"Katana analysis failed: {e}")
        return []

async def run_scrapy_analysis(urls: list, category: str) -> dict:
    """Executar Scrapy usando JSONL gerado pelo katana"""
    try:
        jsonl_file = f"{DATA_DIR}/{category}.jsonl"
        output_file = f"{DATA_DIR}/{category}_seo.json"
        
        # Verificar se JSONL existe
        if not os.path.exists(jsonl_file):
            logger.warning(f"JSONL file not found: {jsonl_file}")
            return {"pages": []}
        
        # Executar Scrapy via script auxiliar para evitar depender de projeto completo
        cmd = [
            "python3",
            SCRAPY_SCRIPT,
            "--input",
            jsonl_file,
            "--output",
            output_file,
            "--category",
            category,
            "--limit",
            "30"
        ]

        logger.info(f"Running scrapy for {category} using script: {' '.join(cmd)}")

        # Executar no diretório do katana-custom
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/app"  # Executar no diretório raiz onde está o scrapy.cfg
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.warning(f"Scrapy output: {stderr.decode()}")
        
        # Ler dados coletados
        try:
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    return json.load(f)
            else:
                logger.warning(f"Scrapy output file not created: {output_file}")
                return {"pages": []}
        except Exception as read_error:
            logger.error(f"Error reading scrapy output: {read_error}")
            return {"pages": []}
        
    except Exception as e:
        logger.error(f"Scrapy analysis failed: {e}")
        return {"pages": []}

def process_category_insights(seo_data: dict, category: str) -> dict:
    """Processar dados coletados em insights para o ICMS"""
    pages = seo_data.get("pages", [])
    
    if not pages:
        # Retornar dados padrão se não conseguir coletar
        return get_fallback_insights(category)
    
    # Calcular métricas
    titles = [p.get("title", "") for p in pages if p.get("title")]
    metas = [p.get("meta_description", "") for p in pages if p.get("meta_description")]
    word_counts = [p.get("word_count", 0) for p in pages if p.get("word_count", 0) > 0]
    
    avg_title_length = sum(len(t) for t in titles) / len(titles) if titles else 50
    avg_meta_length = sum(len(m) for m in metas) / len(metas) if metas else 140
    avg_word_count = sum(word_counts) / len(word_counts) if word_counts else 350
    
    # Extrair keywords comuns
    all_text = " ".join([p.get("title", "") + " " + p.get("meta_description", "") for p in pages])
    keywords = extract_common_keywords(all_text, category)
    
    # Preparar exemplos de concorrentes
    competitor_examples = []
    for page in pages[:3]:  # Top 3
        if page.get("title") and page.get("meta_description"):
            competitor_examples.append({
                "title": page["title"],
                "metaDescription": page["meta_description"],
                "url": page.get("url", "example.com"),
                "score": calculate_seo_score(page)
            })
    
    return {
        "category": category,
        "avgTitleLength": int(avg_title_length),
        "avgMetaLength": int(avg_meta_length),
        "avgWordCount": int(avg_word_count),
        "commonKeywords": keywords,
        "bestPractices": {
            "titlePatterns": [
                "Nome do Negócio + Serviço Principal + Localização",
                "Palavra-chave Principal + Benefício + Call to Action",
                "Serviço + Qualidade + Local"
            ],
            "metaPatterns": [
                "Descrição do serviço + benefício único + call to action",
                "Palavra-chave + diferencial + localização",
                "Problema + solução + resultado"
            ],
            "contentStructure": [
                "Título H1 com palavra-chave principal",
                "Seção sobre serviços com H2",
                "Depoimentos de clientes",
                "Localização e contato",
                "Call to action claro"
            ]
        },
        "competitorExamples": competitor_examples,
        "analysisDate": datetime.now().isoformat(),
        "pagesAnalyzed": len(pages)
    }

def extract_common_keywords(text: str, category: str) -> list:
    """Extrair keywords mais comuns do texto"""
    import re
    from collections import Counter
    
    # Remover pontuação e converter para minúsculas
    words = re.findall(r'\b[a-záàâãéèêíïóôõöúçñ]{3,}\b', text.lower())
    
    # Filtrar stop words básicas
    stop_words = {'que', 'para', 'com', 'uma', 'seu', 'sua', 'nos', 'das', 'dos', 'mais', 'como', 'por', 'são', 'tem', 'ter', 'foi', 'pelo', 'pela'}
    words = [w for w in words if w not in stop_words]
    
    # Contar frequências
    counter = Counter(words)
    
    # Retornar top 6 keywords
    return [word for word, count in counter.most_common(6)]

def calculate_seo_score(page: dict) -> int:
    """Calcular score SEO de uma página"""
    score = 50  # Base
    
    if page.get("title") and len(page["title"]) > 30:
        score += 15
    if page.get("meta_description") and len(page["meta_description"]) > 120:
        score += 15
    if page.get("h1_count", 0) > 0:
        score += 10
    if page.get("word_count", 0) > 300:
        score += 10
    
    return min(100, score)

def get_fallback_insights(category: str) -> dict:
    """Dados de fallback quando não conseguir scraping"""
    fallback_data = {
        "barbearia": {
            "keywords": ["corte masculino", "barba", "cabelo", "barbeiro", "salão", "estilo"],
            "avgTitle": 55, "avgMeta": 145, "avgWords": 420
        },
        "mercearia": {
            "keywords": ["supermercado", "produtos frescos", "entrega", "hortifruti", "mercearia", "qualidade"],
            "avgTitle": 48, "avgMeta": 138, "avgWords": 380
        }
    }
    
    data = fallback_data.get(category, fallback_data["barbearia"])
    
    return {
        "category": category,
        "avgTitleLength": data["avgTitle"],
        "avgMetaLength": data["avgMeta"],
        "avgWordCount": data["avgWords"],
        "commonKeywords": data["keywords"],
        "bestPractices": {
            "titlePatterns": ["Nome + Serviço + Local"],
            "metaPatterns": ["Descrição + Benefício + CTA"],
            "contentStructure": ["H1", "Serviços", "Contato"]
        },
        "competitorExamples": [],
        "fallback": True
    }

async def refresh_category_background(category: str):
    """Refresh dados de categoria em background"""
    try:
        logger.info(f"Background refresh started for {category}")
        
        urls = await run_katana_analysis(category)
        seo_data = await run_scrapy_analysis(urls, category)
        
        # Salvar cache atualizado
        cache_file = f"{DATA_DIR}/{category}_cache.json"
        cache_data = {
            "category": category,
            "last_updated": datetime.now().isoformat(),
            "urls_count": len(urls),
            "pages_analyzed": len(seo_data.get("pages", []))
        }
        
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        
        logger.info(f"Background refresh completed for {category}: {len(urls)} URLs, {len(seo_data.get('pages', []))} pages")
        
    except Exception as e:
        logger.error(f"Background refresh failed for {category}: {e}")

async def create_default_url_list(category: str):
    """Criar lista padrão de URLs para uma categoria"""
    default_urls = {
        "barbearia": [
            "https://www.instagram.com/explore/tags/barbearia/",
            "https://www.google.com/maps/search/barbearia/",
            "https://pt.foursquare.com/explore?mode=url&near=Brasil&q=Barbearia"
        ],
        "mercearia": [
            "https://www.google.com/maps/search/mercado/",
            "https://www.google.com/maps/search/supermercado/",
            "https://pt.foursquare.com/explore?mode=url&near=Brasil&q=Mercado"
        ],
        "auto-center": [
            "https://www.google.com/maps/search/auto+center/",
            "https://www.google.com/maps/search/oficina+mecanica/",
            "https://pt.foursquare.com/explore?mode=url&near=Brasil&q=Auto+Center"
        ],
        "restaurante": [
            "https://www.google.com/maps/search/restaurante/",
            "https://www.ifood.com.br/",
            "https://pt.foursquare.com/explore?mode=url&near=Brasil&q=Restaurante"
        ]
    }
    
    urls = default_urls.get(category, default_urls["barbearia"])
    
    # Criar diretório se não existir
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    urls_file = f"{CONFIG_DIR}/{category}.txt"
    with open(urls_file, "w") as f:
        for url in urls:
            f.write(f"{url}\n")
    
    logger.info(f"Created default URL list for {category} with {len(urls)} URLs")

if __name__ == "__main__":
    try:
        import uvicorn  # type: ignore
    except ImportError as exc:
        raise RuntimeError("uvicorn is required to run the API server locally. Install it via pip.") from exc

    uvicorn.run(app, host="0.0.0.0", port=3001)
