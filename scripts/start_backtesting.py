#!/usr/bin/env python3
"""
QuantROI Backtesting Startup Script

This script provides an easy way to start the backtesting system that goes back in time
to test various trading strategies against historical market data.

Usage:
    python scripts/start_backtesting.py --symbols AAPL,MSFT,SPY --months 12 --strategies all
    python scripts/start_backtesting.py --quick-test  # Run quick 3-month test
    python scripts/start_backtesting.py --help
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import List

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

try:
    from backtesting_engine import BacktestRunner, BacktestingEngine
except ImportError as e:
    print(f"❌ Error importing backtesting engine: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Start QuantROI backtesting system for historical strategy testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/start_backtesting.py --symbols AAPL,MSFT,GOOGL,TSLA,SPY --months 12

  python scripts/start_backtesting.py --quick-test

  python scripts/start_backtesting.py --strategies gated_dql,master_strategy --months 6

  python scripts/start_backtesting.py --start-date 2023-01-01 --end-date 2023-12-31
        """
    )
    
    parser.add_argument(
        '--symbols', 
        type=str, 
        default='AAPL,MSFT,SPY',
        help='Comma-separated list of symbols to test (default: AAPL,MSFT,SPY)'
    )
    
    parser.add_argument(
        '--months', 
        type=int, 
        default=6,
        help='Number of months to look back for testing (default: 6)'
    )
    
    parser.add_argument(
        '--start-date', 
        type=str,
        help='Start date in YYYY-MM-DD format (overrides --months)'
    )
    
    parser.add_argument(
        '--end-date', 
        type=str,
        help='End date in YYYY-MM-DD format (default: today)'
    )
    
    parser.add_argument(
        '--strategies', 
        type=str, 
        default='all',
        help='Comma-separated list of strategies or "all" (default: all)'
    )
    
    parser.add_argument(
        '--quick-test', 
        action='store_true',
        help='Run a quick 3-month test with default settings'
    )
    
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default='backtest_results',
        help='Directory to save results (default: backtest_results)'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def validate_arguments(args):
    """Validate command line arguments"""
    errors = []
    
    if args.start_date:
        try:
            datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            errors.append("Invalid start-date format. Use YYYY-MM-DD")
    
    if args.end_date:
        try:
            datetime.strptime(args.end_date, '%Y-%m-%d')
        except ValueError:
            errors.append("Invalid end-date format. Use YYYY-MM-DD")
    
    if args.months <= 0:
        errors.append("Months must be positive")
    
    symbols = [s.strip().upper() for s in args.symbols.split(',')]
    if not symbols or any(len(s) == 0 for s in symbols):
        errors.append("Invalid symbols format")
    
    if errors:
        print("❌ Validation errors:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)
    
    return True

def setup_output_directory(output_dir: str):
    """Create output directory if it doesn't exist"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")

async def run_backtest_with_config(args):
    """Run backtest with parsed configuration"""
    
    symbols = [s.strip().upper() for s in args.symbols.split(',')]
    
    if args.strategies.lower() == 'all':
        strategies = ['gated_dql', 'gated_pg', 'master_strategy', 'enhanced_master']
    else:
        strategies = [s.strip() for s in args.strategies.split(',')]
    
    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    elif args.start_date:
        start_date = args.start_date
        end_date = datetime.now().strftime('%Y-%m-%d')
    else:
        end_date_obj = datetime.now()
        start_date_obj = end_date_obj - timedelta(days=args.months * 30)
        start_date = start_date_obj.strftime('%Y-%m-%d')
        end_date = end_date_obj.strftime('%Y-%m-%d')
    
    setup_output_directory(args.output_dir)
    
    print("🚀 QuantROI Backtesting System")
    print("=" * 50)
    print(f"📅 Period: {start_date} to {end_date}")
    print(f"📈 Symbols: {', '.join(symbols)}")
    print(f"🧠 Strategies: {', '.join(strategies)}")
    print(f"💾 Output: {args.output_dir}")
    print("=" * 50)
    
    engine = BacktestingEngine(initial_capital=100000.0)
    
    try:
        print("⏳ Loading historical data and running strategies...")
        results = await engine.run_backtest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            strategies=strategies
        )
        
        print_detailed_results(results)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = os.path.join(args.output_dir, f'backtest_results_{timestamp}.json')
        
        save_results_to_file(results, results_file)
        print(f"💾 Detailed results saved to: {results_file}")
        
        summary_file = os.path.join(args.output_dir, f'backtest_summary_{timestamp}.txt')
        generate_summary_report(results, summary_file, symbols, start_date, end_date)
        print(f"📊 Summary report saved to: {summary_file}")
        
        return results
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return None

def print_detailed_results(results):
    """Print detailed backtest results"""
    
    print("\n" + "="*80)
    print("🎯 DETAILED BACKTEST RESULTS")
    print("="*80)
    
    sorted_results = sorted(results.items(), key=lambda x: x[1].total_return, reverse=True)
    
    for i, (strategy_name, result) in enumerate(sorted_results, 1):
        print(f"\n#{i} 📊 {strategy_name.upper().replace('_', ' ')}")
        print("-" * 50)
        print(f"💰 Total Return:     {result.total_return:>8.2%}")
        print(f"📈 Sharpe Ratio:     {result.sharpe_ratio:>8.2f}")
        print(f"📉 Max Drawdown:     {result.max_drawdown:>8.2%}")
        print(f"🎯 Win Rate:         {result.win_rate:>8.2%}")
        print(f"🔄 Total Trades:     {result.total_trades:>8d}")
        print(f"⏱️  Avg Trade Duration: {result.avg_trade_duration:>6.1f}h")
        
        if result.performance_by_period:
            monthly_sorted = sorted(result.performance_by_period.items(), 
                                  key=lambda x: x[1], reverse=True)
            print(f"🏆 Best Months:")
            for month, perf in monthly_sorted[:3]:
                print(f"   {month}: {perf:>6.2%}")
    
    if sorted_results:
        best_strategy = sorted_results[0]
        print(f"\n🏆 CHAMPION STRATEGY: {best_strategy[0].upper().replace('_', ' ')}")
        print(f"🎉 Achieved {best_strategy[1].total_return:.2%} total return")
        
        if len(sorted_results) > 1:
            second_best = sorted_results[1]
            outperformance = best_strategy[1].total_return - second_best[1].total_return
            print(f"📊 Outperformed runner-up by {outperformance:.2%}")

def save_results_to_file(results, filename):
    """Save results to JSON file"""
    import json
    
    json_results = {}
    for strategy, result in results.items():
        json_results[strategy] = {
            'strategy_name': result.strategy_name,
            'total_return': result.total_return,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate,
            'total_trades': result.total_trades,
            'avg_trade_duration': result.avg_trade_duration,
            'performance_by_period': result.performance_by_period,
            'trade_count': len(result.trade_log)
        }
    
    with open(filename, 'w') as f:
        json.dump(json_results, f, indent=2)

def generate_summary_report(results, filename, symbols, start_date, end_date):
    """Generate a text summary report"""
    
    with open(filename, 'w') as f:
        f.write("QuantROI Backtesting Summary Report\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Test Period: {start_date} to {end_date}\n")
        f.write(f"Symbols Tested: {', '.join(symbols)}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        sorted_results = sorted(results.items(), key=lambda x: x[1].total_return, reverse=True)
        
        f.write("STRATEGY RANKINGS BY TOTAL RETURN:\n")
        f.write("-" * 40 + "\n")
        
        for i, (strategy, result) in enumerate(sorted_results, 1):
            f.write(f"{i}. {strategy.upper().replace('_', ' ')}: {result.total_return:.2%}\n")
        
        f.write("\nDETAILED METRICS:\n")
        f.write("-" * 40 + "\n")
        
        for strategy, result in sorted_results:
            f.write(f"\n{strategy.upper().replace('_', ' ')}:\n")
            f.write(f"  Total Return: {result.total_return:.2%}\n")
            f.write(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}\n")
            f.write(f"  Max Drawdown: {result.max_drawdown:.2%}\n")
            f.write(f"  Win Rate: {result.win_rate:.2%}\n")
            f.write(f"  Total Trades: {result.total_trades}\n")

async def main():
    """Main entry point"""
    
    args = parse_arguments()
    
    if args.quick_test:
        args.symbols = 'AAPL,SPY'
        args.months = 3
        args.strategies = 'gated_dql,master_strategy'
        print("🚀 Running quick test with simplified settings...")
    
    validate_arguments(args)
    
    results = await run_backtest_with_config(args)
    
    if results:
        print("\n✅ Backtesting completed successfully!")
        print("🎯 Use the generated files to analyze strategy performance")
        print("💡 Try different time periods and symbols to validate strategies")
    else:
        print("\n❌ Backtesting failed. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Backtesting interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
