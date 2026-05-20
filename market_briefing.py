#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

load_dotenv()

import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from groq import Groq
import discord
from discord.ext import tasks, commands
import asyncio

# 환경변수에서 설정 로드
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq 클라이언트
groq_client = Groq(api_key=GROQ_API_KEY)

# ==================== 웹스크래핑 함수 ====================

def get_korea_market_data():
    """한국 증시 데이터 수집"""
    try:
        # KOSPI 데이터
        kospi = yf.Ticker("^KS11")
        kospi_hist = kospi.history(period="3mo")
        kospi_current = kospi.info.get('currentPrice', 0)
        kospi_change = kospi.info.get('regularMarketChange', 0)
        kospi_change_pct = kospi.info.get('regularMarketChangePercent', 0)
        
        # 20일, 60일 이평선
        kospi_ma20 = kospi_hist['Close'].tail(20).mean()
        kospi_ma60 = kospi_hist['Close'].tail(60).mean()
        
        return {
            'name': 'KOSPI',
            'current': round(kospi_current, 2),
            'change': round(kospi_change, 2),
            'change_pct': round(kospi_change_pct, 2),
            'ma20': round(kospi_ma20, 2),
            'ma60': round(kospi_ma60, 2),
        }
    except Exception as e:
        print(f"Error fetching KOSPI: {e}")
        return None

def get_us_market_data():
    """미국 증시 데이터 수집"""
    try:
        sp500 = yf.Ticker("^GSPC")
        nasdaq = yf.Ticker("^IXIC")
        
        sp500_hist = sp500.history(period="3mo")
        nasdaq_hist = nasdaq.history(period="3mo")
        
        sp500_current = sp500.info.get('currentPrice', 0)
        sp500_change = sp500.info.get('regularMarketChange', 0)
        sp500_change_pct = sp500.info.get('regularMarketChangePercent', 0)
        
        nasdaq_current = nasdaq.info.get('currentPrice', 0)
        nasdaq_change = nasdaq.info.get('regularMarketChange', 0)
        nasdaq_change_pct = nasdaq.info.get('regularMarketChangePercent', 0)
        
        sp500_ma20 = sp500_hist['Close'].tail(20).mean()
        sp500_ma60 = sp500_hist['Close'].tail(60).mean()
        nasdaq_ma20 = nasdaq_hist['Close'].tail(20).mean()
        nasdaq_ma60 = nasdaq_hist['Close'].tail(60).mean()
        
        return {
            'sp500': {
                'name': 'S&P 500',
                'current': round(sp500_current, 2),
                'change': round(sp500_change, 2),
                'change_pct': round(sp500_change_pct, 2),
                'ma20': round(sp500_ma20, 2),
                'ma60': round(sp500_ma60, 2),
            },
            'nasdaq': {
                'name': 'NASDAQ',
                'current': round(nasdaq_current, 2),
                'change': round(nasdaq_change, 2),
                'change_pct': round(nasdaq_change_pct, 2),
                'ma20': round(nasdaq_ma20, 2),
                'ma60': round(nasdaq_ma60, 2),
            }
        }
    except Exception as e:
        print(f"Error fetching US market: {e}")
        return None

def get_korea_news():
    """한경닷컴에서 증시 뉴스 수집"""
    try:
        url = "https://www.hankyung.com/markets"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        
        news_list = []
        articles = soup.find_all('a', class_='tit')[:5]
        
        for article in articles:
            title = article.get_text(strip=True)
            if title and len(title) > 5:
                news_list.append(title)
        
        return news_list if news_list else ["증시 뉴스 수집 실패"]
    except Exception as e:
        print(f"Error fetching Korea news: {e}")
        return ["증시 뉴스 수집 실패"]

def get_us_news():
    """CNN Money에서 미국 증시 뉴스 수집"""
    try:
        url = "https://money.cnn.com/data/markets"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        
        news_list = []
        articles = soup.find_all('span', class_='container__headline-text')[:5]
        
        for article in articles:
            title = article.get_text(strip=True)
            if title and len(title) > 5:
                news_list.append(title)
        
        return news_list if news_list else ["미국 증시 뉴스 수집 실패"]
    except Exception as e:
        print(f"Error fetching US news: {e}")
        return ["미국 증시 뉴스 수집 실패"]

def get_sector_performance():
    """업종별 등락 (상위 3, 하위 3)"""
    try:
        sector_etfs = {
            '에너지': 'XLE',
            '금융': 'XLF',
            '기술': 'XLK',
            '헬스케어': 'XLV',
            '산업': 'XLI',
            '소비재': 'XLY',
            '필수소비': 'XLP',
        }
        
        sector_data = {}
        for sector_name, etf_code in sector_etfs.items():
            try:
                etf = yf.Ticker(etf_code)
                data = etf.info
                change_pct = data.get('regularMarketChangePercent', 0)
                sector_data[sector_name] = round(change_pct, 2)
            except:
                pass
        
        sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1], reverse=True)
        top3 = sorted_sectors[:3]
        bottom3 = sorted_sectors[-3:]
        
        return {
            'top3': top3,
            'bottom3': bottom3,
        }
    except Exception as e:
        print(f"Error fetching sector data: {e}")
        return None

# ==================== 기술적 분석 함수 ====================

def calculate_support_resistance(ma20, ma60, current_price):
    """지지선/저항선 계산"""
    support = min(ma20, ma60)
    resistance = max(ma20, ma60)
    
    return {
        'support': round(support, 2),
        'resistance': round(resistance, 2),
    }

def determine_stance(current, ma20, ma60, change_pct):
    """스탠스 결정 (강세/중립/약세)"""
    if current > ma20 > ma60:
        if change_pct > 0:
            return "강세 (상승 추세 확인)"
        else:
            return "중립 (조정 국면)"
    elif current < ma20 < ma60:
        if change_pct < 0:
            return "약세 (하락 추세 진행중)"
        else:
            return "중립 (반등 신호)"
    else:
        return "중립 (혼조)"

# ==================== Groq AI 분석 ====================

def get_groq_analysis(market_data):
    """Groq AI로 시장 분석 받기"""
    try:
        import json
        prompt = f"""
당신은 전문 증시 분석가입니다. 다음 시장 데이터를 분석하고 간단한 스탠스를 제시해주세요.

시장 데이터:
{json.dumps(market_data, ensure_ascii=False, indent=2)}

분석 요청사항:
1. 현재 시장 상황 요약 (2-3문장)
2. 주요 기술적 신호 (지지선, 저항선 기반)
3. 향후 예상 시나리오 및 투자 스탠스 (강세/중립/약세)
4. 주의할 점

한국어로 간결하게 작성해주세요.
"""
        
        message = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="mixtral-8x7b-32768",
        )
        
        return message.choices[0].message.content
    except Exception as e:
        print(f"Error with Groq API: {e}")
        return "AI 분석 생성 실패"

# ==================== Discord 전송 ====================

class MarketBriefingBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_briefing.start()
    
    @tasks.loop(hours=24)
    async def send_briefing(self):
        """매일 07:30에 브리핑 전송"""
        now = datetime.now()
        target_time = now.replace(hour=7, minute=30, second=0, microsecond=0)
        
        if now > target_time:
            target_time += timedelta(days=1)
        
        wait_seconds = (target_time - now).total_seconds()
        
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        
        # 데이터 수집
        print("[증시 브리핑] 데이터 수집 중...")
        
        kospi = get_korea_market_data()
        us_market = get_us_market_data()
        korea_news = get_korea_news()
        us_news = get_us_news()
        sectors = get_sector_performance()
        
        # 기술적 분석
        if kospi:
            kospi_sr = calculate_support_resistance(kospi['ma20'], kospi['ma60'], kospi['current'])
            kospi['stance'] = determine_stance(kospi['current'], kospi['ma20'], kospi['ma60'], kospi['change_pct'])
            kospi.update(kospi_sr)
        
        if us_market:
            for market_key in ['sp500', 'nasdaq']:
                market = us_market[market_key]
                sr = calculate_support_resistance(market['ma20'], market['ma60'], market['current'])
                market['stance'] = determine_stance(market['current'], market['ma20'], market['ma60'], market['change_pct'])
                market.update(sr)
        
        # AI 분석
        market_analysis_data = {
            'kospi': kospi,
            'us_market': us_market,
            'sectors': sectors,
            'korea_news_sample': korea_news[:3],
            'us_news_sample': us_news[:3],
        }
        
        ai_analysis = get_groq_analysis(market_analysis_data)
        
        # Discord 임베드 메시지 생성
        embed = discord.Embed(
            title="📈 증시 아침 브리핑",
            description=f"{datetime.now().strftime('%Y년 %m월 %d일 %A')}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # KOSPI
        if kospi:
            kospi_text = f"**현재:** {kospi['current']:,.0f}\n**변화:** {kospi['change']:+,.0f} ({kospi['change_pct']:+.2f}%)\n**지지선:** {kospi['support']:,.0f}\n**저항선:** {kospi['resistance']:,.0f}\n**스탠스:** {kospi['stance']}"
            embed.add_field(name="🇰🇷 KOSPI", value=kospi_text, inline=False)
        
        # S&P 500
        if us_market:
            sp500 = us_market['sp500']
            sp500_text = f"**현재:** {sp500['current']:,.0f}\n**변화:** {sp500['change']:+,.0f} ({sp500['change_pct']:+.2f}%)\n**지지선:** {sp500['support']:,.0f}\n**저항선:** {sp500['resistance']:,.0f}\n**스탠스:** {sp500['stance']}"
            embed.add_field(name="🇺🇸 S&P 500", value=sp500_text, inline=False)
            
            # NASDAQ
            nasdaq = us_market['nasdaq']
            nasdaq_text = f"**현재:** {nasdaq['current']:,.0f}\n**변화:** {nasdaq['change']:+,.0f} ({nasdaq['change_pct']:+.2f}%)\n**지지선:** {nasdaq['support']:,.0f}\n**저항선:** {nasdaq['resistance']:,.0f}\n**스탠스:** {nasdaq['stance']}"
            embed.add_field(name="📊 NASDAQ", value=nasdaq_text, inline=False)
        
        # 업종별 상위/하위
        if sectors:
            top_sector = ", ".join([f"{s[0]} {s[1]:+.2f}%" for s in sectors['top3']])
            bottom_sector = ", ".join([f"{s[0]} {s[1]:+.2f}%" for s in sectors['bottom3']])
            embed.add_field(name="📍 업종별 등락", value=f"**상위 3:** {top_sector}\n**하위 3:** {bottom_sector}", inline=False)
        
        # 주요 뉴스
        korea_news_str = "\n".join([f"• {news[:50]}..." if len(news) > 50 else f"• {news}" for news in korea_news[:3]])
        us_news_str = "\n".join([f"• {news[:50]}..." if len(news) > 50 else f"• {news}" for news in us_news[:3]])
        
        embed.add_field(name="📰 한국 증시 뉴스", value=korea_news_str or "뉴스 없음", inline=False)
        embed.add_field(name="📰 미국 증시 뉴스", value=us_news_str or "뉴스 없음", inline=False)
        
        # AI 분석
        ai_text = ai_analysis[:1000] if len(ai_analysis) > 1000 else ai_analysis
        embed.add_field(name="🤖 AI 분석", value=ai_text, inline=False)
        
        # Discord에 전송
        channel = self.bot.get_channel(CHANNEL_ID)
        if channel:
            try:
                await channel.send(embed=embed)
                print("[증시 브리핑] 전송 완료!")
            except Exception as e:
                print(f"Error sending message: {e}")
        else:
            print(f"Channel {CHANNEL_ID} not found")
    
    @send_briefing.before_loop
    async def before_send_briefing(self):
        await self.bot.wait_until_ready()

# ==================== 메인 ====================

def main():
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'{bot.user} has connected to Discord!')
    
    async def load_cog():
        await bot.add_cog(MarketBriefingBot(bot))
    
    async def run_bot():
        await load_cog()
        await bot.start(DISCORD_TOKEN)
    
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()