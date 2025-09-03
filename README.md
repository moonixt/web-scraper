# 🕷️ Katana + Scrapy Integration

Uma integração poderosa entre **Katana** (descoberta de URLs) e **Scrapy** (web scraping) para coleta automatizada de conteúdo web e imagens.

## 📋 Índice

- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso Básico](#uso-básico)
- [Comandos Úteis](#comandos-úteis)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Configurações Avançadas](#configurações-avançadas)
- [Exemplos de Uso](#exemplos-de-uso)
- [Troubleshooting](#troubleshooting)

## 🚀 Instalação

### Dependências Principais

```bash
# Scrapy e dependências
pip install scrapy beautifulsoup4 Pillow

# Katana (ProjectDiscovery)
go install github.com/projectdiscovery/katana/cmd/katana@latest

# Ou usando conda
conda install -c conda-forge scrapy beautifulsoup4 pillow
```

### Verificar Instalação

```bash
# Verificar Scrapy
scrapy version

# Verificar Katana
katana -version

# Verificar Pillow
python -c "from PIL import Image; print('Pillow OK')"
```

## ⚙️ Configuração

### 1. Configuração do Scrapy (`settings.py`)

```python
# Pipeline de imagens
ITEM_PIPELINES = {
    'scrapy.pipelines.images.ImagesPipeline': 1,
}

# Configurações de imagens
IMAGES_STORE = 'images'
IMAGES_MIN_HEIGHT = 50
IMAGES_MIN_WIDTH = 50

# Outras configurações úteis
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True
```

### 2. Estrutura de Items (`items.py`)

```python
import scrapy

class PageItem(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    content = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()
```

## 🎯 Uso Básico

### 1. Gerar URLs com Katana

```bash
# Descoberta básica de URLs
katana -u https://exemplo.com -o urls.jsonl

# Descoberta com profundidade
katana -u https://exemplo.com -d 3 -o urls_deep.jsonl

# Descoberta com filtros
katana -u https://exemplo.com -f qurl -o urls_filtered.jsonl

# Múltiplos domínios
katana -list targets.txt -o urls_multi.jsonl
```

### 2. Executar Spider com Katana

```bash
# Comando básico
scrapy crawl page -a katana_file="urls.jsonl"

# Especificar spider específico
scrapy crawl page -a katana_file="urls.jsonl" -s SPIDER_MODULES=tutorial.spiders.crawlocal

# Com configurações customizadas
scrapy crawl page -a katana_file="urls.jsonl" -s IMAGES_STORE=custom_images -s DOWNLOAD_DELAY=2
```

## 📚 Comandos Úteis

### Comandos Katana

```bash
# Descoberta básica
katana -u https://site.com -o output.jsonl

# Com maior profundidade
katana -u https://site.com -d 5 -o deep_crawl.jsonl

# Apenas subdomínios
katana -u https://site.com -field-scope subs -o subdomains.jsonl

# Com rate limiting
katana -u https://site.com -rl 100 -o rate_limited.jsonl

# Salvar apenas URLs únicas
katana -u https://site.com -f qurl -unique -o unique_urls.jsonl

# Descoberta com JavaScript rendering
katana -u https://site.com -js-crawl -o js_rendered.jsonl

# Filtrar por extensões
katana -u https://site.com -ef png,jpg,gif -o no_images.jsonl

# Timeout customizado
katana -u https://site.com -timeout 30 -o timeout_30s.jsonl
```

### Comandos Scrapy

```bash
# Listar spiders disponíveis
scrapy list

# Executar com log detalhado
scrapy crawl page -a katana_file="urls.jsonl" -L DEBUG

# Salvar logs em arquivo
scrapy crawl page -a katana_file="urls.jsonl" -L INFO -s LOG_FILE=scrapy.log

# Executar em background
nohup scrapy crawl page -a katana_file="urls.jsonl" > output.log 2>&1 &

# Parar execução após X itens
scrapy crawl page -a katana_file="urls.jsonl" -s CLOSESPIDER_ITEMCOUNT=100

# Configurar User-Agent
scrapy crawl page -a katana_file="urls.jsonl" -s USER_AGENT="Custom Bot 1.0"

# Desabilitar robots.txt
scrapy crawl page -a katana_file="urls.jsonl" -s ROBOTSTXT_OBEY=False

# Configurar proxy
scrapy crawl page -a katana_file="urls.jsonl" -s HTTP_PROXY=http://proxy:8080
```

### Comandos de Análise

```bash
# Contar URLs no arquivo Katana
wc -l urls.jsonl

# Ver primeiras URLs
head -5 urls.jsonl

# Extrair apenas URLs (formato Katana)
cat urls.jsonl | jq -r '.request.endpoint' | head -10

# Contar domínios únicos
cat urls.jsonl | jq -r '.request.endpoint' | cut -d'/' -f3 | sort | uniq -c

# Verificar arquivos gerados
find . -name "scraped_*" -type d

# Contar arquivos HTML gerados
find . -name "*.html" | wc -l

# Verificar estrutura de imagens organizadas
find images/ -type f | sort

# Ver imagens por arquivo JSON específico
ls images/test/
ls images/test_simple/

# Contar imagens por pasta
find images/ -name "*.jpg" -o -name "*.png" | cut -d'/' -f2 | sort | uniq -c

# Tamanho de imagens por pasta
du -sh images/*/

# Estatísticas de execução
grep "item_scraped_count\|file_count" scrapy.log
```

### 📊 Comandos de Organização

```bash
# Ver estrutura completa organizada
find . -name "scraped_*" -o -name "images" | sort

# Contar arquivos por projeto
for dir in scraped_*; do echo "$dir: $(ls $dir | wc -l) arquivos"; done

# Verificar imagens por arquivo JSON
for dir in images/*/; do echo "$(basename $dir): $(ls $dir | wc -l) imagens"; done

# Limpar execuções antigas (cuidado!)
rm -rf scraped_* images/*/

# Backup de resultados por data
tar -czf backup_$(date +%Y%m%d).tar.gz scraped_* images/
```

## 📁 Estrutura do Projeto

```
tutorial/
├── scrapy.cfg              # Configuração do projeto Scrapy
├── tutorial/
│   ├── __init__.py
│   ├── items.py            # Definição dos items
│   ├── middlewares.py      # Middlewares customizados
│   ├── pipelines.py        # Pipeline customizado de imagens
│   ├── settings.py         # Configurações do Scrapy
│   └── spiders/
│       ├── __init__.py
│       ├── crawlocal.py    # Spider principal
│       ├── test.jsonl      # Arquivo Katana (formato completo)
│       ├── test_simple.jsonl # Arquivo simplificado
│       └── teste_final.jsonl # Exemplo de teste
├── images/                 # Imagens baixadas (organizadas por arquivo JSON)
│   ├── test/               # Imagens do arquivo test.jsonl
│   │   ├── [hash].jpg
│   │   └── [hash].png
│   ├── test_simple/        # Imagens do arquivo test_simple.jsonl
│   │   ├── [hash].jpg
│   │   └── [hash].png
│   └── teste_final/        # Imagens do arquivo teste_final.jsonl
│       ├── [hash].jpg
│       └── [hash].png
├── scraped_[filename]/     # Conteúdo extraído (organizado por arquivo JSON)
│   ├── page-[url].html     # HTML original
│   └── pretty-[url].html   # HTML formatado
└── README.md
```

### 🗂️ Organização Automática

O sistema agora organiza automaticamente tanto **imagens** quanto **conteúdo** baseado no nome do arquivo JSON de entrada:

- **Imagens**: `images/[nome_arquivo]/[hash].[ext]`
- **Conteúdo**: `scraped_[nome_arquivo]/[arquivos_html]`

**Exemplo:**
```bash
# Para arquivo test.jsonl
images/test/          # Imagens
scraped_test/         # Conteúdo HTML

# Para arquivo blog_urls.jsonl  
images/blog_urls/     # Imagens
scraped_blog_urls/    # Conteúdo HTML
```

## 🔧 Configurações Avançadas

### Pipeline Customizado de Imagens

O projeto inclui um pipeline customizado que organiza imagens por nome do arquivo JSON:

```python
# settings.py
ITEM_PIPELINES = {
    'tutorial.pipelines.CustomImagesPipeline': 1,
}

# Configurações de imagem
IMAGES_STORE = 'images'
IMAGES_MIN_HEIGHT = 50
IMAGES_MIN_WIDTH = 50
IMAGES_EXPIRES = 90  # dias
```

### Estrutura de Organização

- **Por arquivo JSON**: Cada execução cria pastas baseadas no nome do arquivo
- **Imagens separadas**: `images/[nome_arquivo]/`
- **Conteúdo separado**: `scraped_[nome_arquivo]/`
- **Nomes únicos**: Imagens com hash SHA1 da URL

### Rate Limiting e Delays

```python
# settings.py
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
```

### Headers Customizados

```python
# settings.py
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'User-Agent': 'Mozilla/5.0 (compatible; MyBot/1.0)',
}
```

## 💡 Exemplos de Uso

### Workflow Completo

```bash
# 1. Descobrir URLs com Katana
katana -u https://blog.exemplo.com -d 2 -o blog_urls.jsonl

# 2. Executar spider Scrapy
scrapy crawl page -a katana_file="blog_urls.jsonl"

# 3. Verificar resultados
ls scraped_blog_urls/
ls images/full/

# 4. Análise dos dados
find scraped_blog_urls/ -name "*.html" | wc -l
du -sh images/
```

### Scraping de E-commerce

```bash
# Descobrir páginas de produtos
katana -u https://loja.com -f qurl -ef css,js -o produtos.jsonl

# Scraping focado em imagens
scrapy crawl page -a katana_file="produtos.jsonl" -s IMAGES_MIN_HEIGHT=200
```

### Monitoramento de Site

```bash
# Descoberta diária
katana -u https://noticias.com -d 1 -o noticias_$(date +%Y%m%d).jsonl

# Scraping automatizado
scrapy crawl page -a katana_file="noticias_$(date +%Y%m%d).jsonl"
```

## 🚨 Troubleshooting

### Problemas Comuns

#### 1. Erro: "Multiple spiders found"
```bash
# Solução: Especificar o módulo do spider
scrapy crawl page -a katana_file="urls.jsonl" -s SPIDER_MODULES=tutorial.spiders.crawlocal
```

#### 2. Erro: "ImagesPipeline requires Pillow"
```bash
# Solução: Instalar/atualizar Pillow
pip install --upgrade Pillow
```

#### 3. Arquivo Katana vazio
```bash
# Verificar formato do arquivo
head -3 urls.jsonl
# Se vazio, regenerar com Katana
katana -u https://site.com -o urls.jsonl
```

#### 4. Muitas requisições/Rate limiting
```bash
# Adicionar delay
scrapy crawl page -a katana_file="urls.jsonl" -s DOWNLOAD_DELAY=5
```

### Logs e Debug

```bash
# Debug completo
scrapy crawl page -a katana_file="urls.jsonl" -L DEBUG

# Salvar logs
scrapy crawl page -a katana_file="urls.jsonl" -L INFO -s LOG_FILE=debug.log

# Verificar estatísticas
grep -E "(item_scraped_count|file_count|elapsed_time)" debug.log
```

## 📊 Formatos Suportados

### Formato Katana Original
```json
{
  "timestamp": "2025-09-03T02:30:00Z",
  "request": {
    "method": "GET",
    "endpoint": "https://exemplo.com/pagina"
  },
  "response": {
    "status_code": 200
  }
}
```

### Formato Simplificado
```json
{
  "url": "https://exemplo.com/pagina"
}
```

## 🏆 Características

- ✅ **Dual Format**: Suporta formato Katana e simplificado
- ✅ **Auto Organization**: Pastas nomeadas automaticamente por arquivo JSON
- ✅ **Separated Images**: Imagens organizadas por origem do arquivo
- ✅ **Separated Content**: Conteúdo HTML organizado por origem do arquivo
- ✅ **Image Pipeline**: Download automático de imagens com detecção de extensão
- ✅ **Content Processing**: HTML original + formatado
- ✅ **URL Filtering**: Remove duplicatas e URLs inválidas
- ✅ **Hash Naming**: Nomes únicos baseados em hash SHA1
- ✅ **Error Handling**: Tratamento robusto de erros
- ✅ **Scalable**: Processa milhares de URLs
- ✅ **Configurable**: Altamente customizável

## 📝 Licença

Este projeto é fornecido como está, para fins educacionais e de pesquisa. Respeite sempre os robots.txt e políticas dos sites.

