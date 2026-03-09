#!/usr/bin/env python
"""
Urban Pulse Backend - CLI Tool
Provides command-line interface for system operations.
"""

import click
import asyncio
import logging
from pathlib import Path
from tabulate import tabulate
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Urban Pulse Backend Management CLI"""
    pass


@cli.command()
@click.option('--clear', is_flag=True, help='Clear existing data first')
def load_data(clear):
    """Load Zillow data into MongoDB"""
    from src.pipeline.data_processor import DataProcessor
    from src.core.database import db
    import asyncio
    
    async def _load():
        await db.connect()
        try:
            if clear:
                logger.info("Clearing existing data...")
                await db.clear_all_data()
            
            processor = DataProcessor()
            properties_list, borough_list = processor.process_full_pipeline()
            
            logger.info("Upserting properties...")
            props_count = await db.upsert_properties(properties_list)
            
            logger.info("Upserting borough metrics...")
            boroughs_count = await db.upsert_borough_metrics(borough_list)
            
            click.echo(click.style("✓ Data loaded successfully", fg='green'))
            click.echo(f"  Properties: {props_count}")
            click.echo(f"  Boroughs: {boroughs_count}")
        finally:
            await db.disconnect()
    
    asyncio.run(_load())


@cli.command()
def show_stats():
    """Display database statistics"""
    from src.core.database import db
    import asyncio
    
    async def _stats():
        await db.connect()
        try:
            analytics = await db.get_analytics_summary()
            
            click.echo("\n" + click.style("=" * 60, fg='blue'))
            click.echo(click.style("Urban Pulse Database Statistics", fg='blue', bold=True))
            click.echo(click.style("=" * 60, fg='blue'))
            
            click.echo(f"\nTotal Properties: {analytics['total_properties']}")
            click.echo(f"Total Boroughs: {analytics['total_boroughs']}")
            click.echo(f"Avg Borough Score: {analytics['avg_borough_opportunity_score']:.2f}")
            click.echo(f"Best Borough: {analytics['highest_opportunity_borough']}")
            click.echo(f"Worst Borough: {analytics['lowest_opportunity_borough']}")
            
            if analytics['market_statistics']:
                click.echo("\n" + click.style("Market Statistics:", fg='cyan'))
                stats = analytics['market_statistics']
                for key, value in stats.items():
                    if isinstance(value, float):
                        click.echo(f"  {key}: {value:,.2f}")
                    else:
                        click.echo(f"  {key}: {value}")
            
            click.echo("\n" + click.style("=" * 60, fg='blue'))
        finally:
            await db.disconnect()
    
    asyncio.run(_stats())


@cli.command()
@click.option('--sort', default='opportunity_score', help='Sort by field')
@click.option('--limit', default=10, help='Number of rows to show')
def show_boroughs(sort, limit):
    """Display borough metrics"""
    from src.core.database import db
    import asyncio
    
    async def _boroughs():
        await db.connect()
        try:
            boroughs = await db.get_all_boroughs()
            
            if not boroughs:
                click.echo("No boroughs found")
                return
            
            # Sort
            boroughs = sorted(boroughs, key=lambda x: x.get(sort, 0), reverse=True)[:limit]
            
            # Prepare table data
            rows = []
            for i, b in enumerate(boroughs, 1):
                rows.append([
                    i,
                    b['borough_name'],
                    f"{b['property_count']}",
                    f"${b['avg_price']:,.0f}",
                    f"{b['avg_demand_score']:.1f}",
                    f"{b['opportunity_score']:.1f}"
                ])
            
            headers = ['#', 'Borough', 'Properties', 'Avg Price', 'Demand', 'Opp. Score']
            
            click.echo("\n" + click.style("Top Boroughs by Opportunity Score", fg='green', bold=True))
            click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
            
        finally:
            await db.disconnect()
    
    asyncio.run(_boroughs())


@cli.command()
@click.argument('api_url', default='http://localhost:8000')
def test_api(api_url):
    """Test API endpoints"""
    click.echo(f"\nTesting API at {api_url}...\n")
    
    tests = [
        ("Health Check", "GET", "/health"),
        ("API Status", "GET", "/api/status"),
        ("Get Boroughs", "GET", "/api/boroughs?limit=5"),
        ("Get Analytics", "GET", "/api/analytics"),
    ]
    
    results = []
    for name, method, endpoint in tests:
        try:
            url = f"{api_url}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            
            status = f"{response.status_code}"
            if response.status_code == 200:
                status = click.style("✓ OK", fg='green')
            else:
                status = click.style(f"✗ {response.status_code}", fg='red')
            
            results.append([name, status])
        except Exception as e:
            results.append([name, click.style(f"✗ Error: {str(e)}", fg='red')])
    
    headers = ['Test', 'Result']
    click.echo(tabulate(results, headers=headers, tablefmt='grid'))


@cli.command()
def create_indexes():
    """Create database indexes"""
    from database import db
    import asyncio
    
    async def _create():
        await db.connect()
        try:
            await db._create_indexes()
            click.echo(click.style("✓ Indexes created successfully", fg='green'))
        finally:
            await db.disconnect()
    
    asyncio.run(_create())


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to clear all data?')
def clear_data():
    """Clear all data from database"""
    from database import db
    import asyncio
    
    async def _clear():
        await db.connect()
        try:
            await db.clear_all_data()
            click.echo(click.style("✓ All data cleared", fg='green'))
        finally:
            await db.disconnect()
    
    asyncio.run(_clear())


@cli.command()
def config_show():
    """Show current configuration"""
    from config import settings
    
    click.echo("\n" + click.style("Current Configuration", fg='cyan', bold=True))
    click.echo(click.style("=" * 50, fg='cyan'))
    
    config_vars = [
        ('MongoDB URL', settings.MONGODB_URL),
        ('Database Name', settings.MONGODB_DB_NAME),
        ('Zillow Data', settings.ZILLOW_DATA_PATH),
        ('Log Level', settings.LOG_LEVEL),
        ('API Title', settings.API_TITLE),
    ]
    
    for key, value in config_vars:
        click.echo(f"{key:.<30} {value}")
    
    click.echo(click.style("=" * 50, fg='cyan'))


if __name__ == '__main__':
    cli()
