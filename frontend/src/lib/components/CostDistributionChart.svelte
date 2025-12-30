<script lang="ts">
	import { PieChart } from 'layerchart';
	import { formatCurrency, parsePrice, isPercentagePrice } from '$lib/utils';
	import type { Product } from '$lib/api';

	interface LineItem {
		id: string;
		product: Product | null;
		quantity: number;
		isAllotment?: boolean;
	}

	export let lines: LineItem[] = [];
	export let billingType: 'annually' | 'monthly' | 'on_demand' = 'annually';

	// Color palette for categories
	const categoryColors: Record<string, string> = {
		'APM': 'hsl(262, 83%, 58%)', // Purple (Datadog purple)
		'Log Management': 'hsl(142, 76%, 36%)', // Green
		'Infrastructure': 'hsl(217, 91%, 60%)', // Blue
		'RUM & Session Replay': 'hsl(25, 95%, 53%)', // Orange
		'Synthetics': 'hsl(340, 82%, 52%)', // Pink
		'Database Monitoring': 'hsl(47, 96%, 53%)', // Yellow
		'Network Monitoring': 'hsl(199, 89%, 48%)', // Cyan
		'Security': 'hsl(0, 72%, 51%)', // Red
		'CI/CD': 'hsl(271, 91%, 65%)', // Violet
		'Serverless': 'hsl(160, 84%, 39%)', // Teal
	};

	// Default color for unknown categories
	const defaultColors = [
		'hsl(215, 20%, 65%)',
		'hsl(215, 20%, 55%)',
		'hsl(215, 20%, 45%)',
		'hsl(215, 20%, 35%)',
	];

	function getCategoryColor(category: string, index: number): string {
		return categoryColors[category] || defaultColors[index % defaultColors.length];
	}

	function getPriceField(product: Product): string {
		switch (billingType) {
			case 'annually': return product.billed_annually;
			case 'monthly': return product.billed_month_to_month;
			case 'on_demand': return product.on_demand;
		}
	}

	// Calculate costs grouped by category
	$: categoryData = (() => {
		const categories: Record<string, { cost: number; products: string[] }> = {};
		
		for (const line of lines) {
			if (!line.product || line.isAllotment) continue;
			
			const category = line.product.category || 'Other';
			const priceStr = getPriceField(line.product);
			
			// Skip percentage-based pricing for now
			if (isPercentagePrice(priceStr)) continue;
			
			const price = parsePrice(priceStr);
			const lineCost = price * line.quantity;
			
			if (!categories[category]) {
				categories[category] = { cost: 0, products: [] };
			}
			categories[category].cost += lineCost;
			if (!categories[category].products.includes(line.product.product)) {
				categories[category].products.push(line.product.product);
			}
		}
		
		return categories;
	})();

	// Convert to chart data format
	$: chartData = (() => {
		const data = Object.entries(categoryData)
			.filter(([_, v]) => v.cost > 0)
			.map(([category, data], index) => ({
				category,
				cost: data.cost * 12, // Annual cost
				products: data.products,
				color: getCategoryColor(category, index),
			}))
			.sort((a, b) => b.cost - a.cost);
		
		return data;
	})();

	// Calculate total for percentages
	$: totalCost = chartData.reduce((sum, d) => sum + d.cost, 0);

	// Create a unique key based on the data to force re-render
	$: chartKey = chartData.map(d => `${d.category}:${d.cost}`).join('|');

	// Legend items
	$: legendItems = chartData.map(d => ({
		name: d.category,
		color: d.color,
		percentage: totalCost > 0 ? (d.cost / totalCost) * 100 : 0,
		value: formatCurrency(d.cost),
	}));
</script>

{#if chartData.length > 0}
	<div class="flex flex-col lg:flex-row items-center gap-6">
		<!-- Donut Chart -->
		<div class="w-[200px] h-[200px] relative">
			{#key chartKey}
				<PieChart
					data={chartData}
					key="category"
					value="cost"
					c="color"
					innerRadius={0.6}
					legend={false}
				/>
			{/key}
			<!-- Center text -->
			<div class="absolute inset-0 flex items-center justify-center pointer-events-none">
				<div class="text-center">
					<div class="text-lg font-bold">{formatCurrency(totalCost)}</div>
					<div class="text-xs text-muted-foreground">/year</div>
				</div>
			</div>
		</div>

		<!-- Legend -->
		<div class="flex-1">
			<div class="flex flex-col gap-2 text-sm">
				{#each legendItems as item}
					<div class="flex items-center gap-2">
						<div
							class="h-3 w-3 rounded-sm shrink-0"
							style="background-color: {item.color}"
						></div>
						<span class="text-muted-foreground">{item.name}</span>
						<span class="font-medium">{item.percentage.toFixed(1)}%</span>
						<span class="text-muted-foreground text-xs">({item.value})</span>
					</div>
				{/each}
			</div>
		</div>
	</div>
{:else}
	<div class="text-center text-muted-foreground py-8">
		Add products to see cost distribution
	</div>
{/if}

<style>
	/* Override layerchart styles to fit within container */
	:global(.chart-container) {
		width: 100%;
		height: 100%;
	}
</style>
