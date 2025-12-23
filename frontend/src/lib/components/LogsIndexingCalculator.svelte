<script lang="ts">
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import { formatCurrency, formatNumber } from '$lib/utils';
	import type { Product } from '$lib/api';

	export let products: Product[] = [];
	export let onAddToQuote: (items: { product: Product; quantity: number }[]) => void = () => {};

	// User inputs
	let ingestedLogsGB = 100; // GB per month
	let avgLogSizeKB = 2; // Average log size in KB
	let indexingPercentage = 15; // Percentage of logs to index
	let retentionDays: 3 | 7 | 15 | 30 = 15;

	// Additional options (collapsible)
	let showAdditionalOptions = false;
	let enableFlexStarter = false;
	let enableFlexStorage = false;
	let enableForwarding = false;
	let flexStarterGB = 10; // GB per month
	let flexStorageGB = 50; // GB per month
	let forwardingGB = 20; // GB per month

	// Use case presets
	const useCasePresets = [
		{ name: 'Minimal (Errors only)', percentage: 5, description: 'Index only errors and critical events' },
		{ name: 'Standard (Debug + Errors)', percentage: 15, description: 'Index errors, warnings, and key debug logs' },
		{ name: 'Extended (Most logs)', percentage: 30, description: 'Index most logs for thorough debugging' },
		{ name: 'Compliance (All logs)', percentage: 100, description: 'Index all logs for compliance requirements' },
	];

	// Retention options
	const retentionOptions = [
		{ days: 3, label: '3 days', description: 'Short-term debugging' },
		{ days: 7, label: '7 days', description: 'Weekly analysis' },
		{ days: 15, label: '15 days', description: 'Standard retention' },
		{ days: 30, label: '30 days', description: 'Extended retention' },
	];

	// Calculate derived values
	$: totalLogsPerMonth = (ingestedLogsGB * 1024 * 1024) / avgLogSizeKB; // Total number of logs
	$: indexedLogsCount = totalLogsPerMonth * (indexingPercentage / 100);
	$: indexedLogsInMillions = indexedLogsCount / 1_000_000;

	// Find relevant products
	$: ingestionProduct = products.find(p => 
		p.product.toLowerCase().includes('logs') && 
		p.product.toLowerCase().includes('ingestion')
	);

	$: indexedProduct = products.find(p => 
		p.product.toLowerCase().includes('indexed log events') &&
		p.billing_unit.toLowerCase().includes(`${retentionDays}-day`)
	);

	// Additional products
	$: flexStarterProduct = products.find(p => p.product === 'Flex Logs Starter');
	$: flexStorageProduct = products.find(p => p.product === 'Flex Logs Storage');
	$: forwardingProduct = products.find(p => p.product === 'Logs - Forwarding to Custom Destinations');

	// Parse prices
	function parsePrice(priceStr: string | null): number {
		if (!priceStr) return 0;
		const match = priceStr.match(/[\d.]+/);
		return match ? parseFloat(match[0]) : 0;
	}

	$: ingestionPrice = parsePrice(ingestionProduct?.billed_annually);
	$: indexedPrice = parsePrice(indexedProduct?.billed_annually);
	$: flexStarterPrice = parsePrice(flexStarterProduct?.billed_annually);
	$: flexStoragePrice = parsePrice(flexStorageProduct?.billed_annually);
	$: forwardingPrice = parsePrice(forwardingProduct?.billed_annually);

	// Calculate costs
	$: ingestionCost = ingestedLogsGB * ingestionPrice;
	$: indexedCost = indexedLogsInMillions * indexedPrice;
	$: flexStarterCost = enableFlexStarter ? flexStarterGB * flexStarterPrice : 0;
	$: flexStorageCost = enableFlexStorage ? flexStorageGB * flexStoragePrice : 0;
	$: forwardingCost = enableForwarding ? forwardingGB * forwardingPrice : 0;
	$: additionalCost = flexStarterCost + flexStorageCost + forwardingCost;
	$: totalMonthlyCost = ingestionCost + indexedCost + additionalCost;
	$: totalAnnualCost = totalMonthlyCost * 12;

	// Cost breakdown percentages
	$: ingestionCostPercent = totalMonthlyCost > 0 ? (ingestionCost / totalMonthlyCost) * 100 : 0;
	$: indexedCostPercent = totalMonthlyCost > 0 ? (indexedCost / totalMonthlyCost) * 100 : 0;
	$: additionalCostPercent = totalMonthlyCost > 0 ? (additionalCost / totalMonthlyCost) * 100 : 0;

	function applyPreset(percentage: number) {
		indexingPercentage = percentage;
	}

	function addToQuote() {
		const items: { product: Product; quantity: number }[] = [];
		
		if (ingestionProduct && ingestedLogsGB > 0) {
			items.push({ product: ingestionProduct, quantity: Math.ceil(ingestedLogsGB) });
		}
		
		if (indexedProduct && indexedLogsInMillions > 0) {
			items.push({ product: indexedProduct, quantity: Math.ceil(indexedLogsInMillions) });
		}

		// Additional products
		if (enableFlexStarter && flexStarterProduct && flexStarterGB > 0) {
			items.push({ product: flexStarterProduct, quantity: Math.ceil(flexStarterGB) });
		}
		
		if (enableFlexStorage && flexStorageProduct && flexStorageGB > 0) {
			items.push({ product: flexStorageProduct, quantity: Math.ceil(flexStorageGB) });
		}
		
		if (enableForwarding && forwardingProduct && forwardingGB > 0) {
			items.push({ product: forwardingProduct, quantity: Math.ceil(forwardingGB) });
		}
		
		if (items.length > 0) {
			onAddToQuote(items);
		}
	}
</script>

<Card class="border-datadog-purple/20">
	<CardHeader>
		<div class="flex items-center gap-3">
			<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-datadog-purple to-datadog-blue">
				<svg class="h-5 w-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
					<polyline points="14 2 14 8 20 8" />
					<line x1="16" y1="13" x2="8" y2="13" />
					<line x1="16" y1="17" x2="8" y2="17" />
					<polyline points="10 9 9 9 8 9" />
				</svg>
			</div>
			<div>
				<CardTitle>Log Indexing Estimator</CardTitle>
				<CardDescription>Estimate your log indexing needs based on ingestion volume</CardDescription>
			</div>
		</div>
	</CardHeader>
	<CardContent class="space-y-6">
		<!-- Input Section -->
		<div class="grid gap-6 md:grid-cols-2">
			<!-- Ingested Logs -->
			<div class="space-y-2">
				<label class="text-sm font-medium">Ingested Logs (GB/month)</label>
				<Input 
					type="number" 
					bind:value={ingestedLogsGB} 
					min="1" 
					class="font-mono"
				/>
				<p class="text-xs text-muted-foreground">Total volume of logs ingested into Datadog</p>
			</div>

			<!-- Average Log Size -->
			<div class="space-y-2">
				<label class="text-sm font-medium">Average Log Size (KB)</label>
				<Input 
					type="number" 
					bind:value={avgLogSizeKB} 
					min="0.1" 
					step="0.1"
					class="font-mono"
				/>
				<p class="text-xs text-muted-foreground">Typical log entry size (default: 2KB)</p>
			</div>
		</div>

		<!-- Retention Selection -->
		<div class="space-y-3">
			<span class="text-sm font-medium">Index Retention Period</span>
			<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
				{#each retentionOptions as option}
					<button
						type="button"
						class="rounded-lg border p-3 text-left transition-all {retentionDays === option.days 
							? 'border-datadog-purple bg-datadog-purple/10 ring-2 ring-datadog-purple' 
							: 'border-border hover:border-muted-foreground'}"
						on:click={() => retentionDays = option.days}
					>
						<div class="font-medium">{option.label}</div>
						<div class="text-xs text-muted-foreground">{option.description}</div>
					</button>
				{/each}
			</div>
		</div>

		<!-- Indexing Percentage -->
		<div class="space-y-3">
			<div class="flex items-center justify-between">
				<span class="text-sm font-medium">Indexing Percentage</span>
				<span class="font-mono text-lg font-bold text-datadog-purple">{indexingPercentage}%</span>
			</div>
			<input 
				type="range" 
				bind:value={indexingPercentage} 
				min="1" 
				max="100" 
				class="w-full accent-datadog-purple"
			/>
			<div class="flex justify-between text-xs text-muted-foreground">
				<span>1% (Minimal)</span>
				<span>100% (All)</span>
			</div>
		</div>

		<!-- Use Case Presets -->
		<div class="space-y-3">
			<span class="text-sm font-medium">Quick Presets</span>
			<div class="grid gap-2 sm:grid-cols-2">
				{#each useCasePresets as preset}
					<button
						type="button"
						class="rounded-lg border p-3 text-left transition-all {indexingPercentage === preset.percentage 
							? 'border-datadog-green bg-datadog-green/10' 
							: 'border-border hover:border-muted-foreground'}"
						on:click={() => applyPreset(preset.percentage)}
					>
						<div class="flex items-center justify-between">
							<span class="font-medium">{preset.name}</span>
							<span class="font-mono text-sm text-muted-foreground">{preset.percentage}%</span>
						</div>
						<div class="text-xs text-muted-foreground mt-1">{preset.description}</div>
					</button>
				{/each}
			</div>
		</div>

		<!-- Additional Options (Collapsible) -->
		<div class="border border-border rounded-lg overflow-hidden">
			<button
				type="button"
				class="w-full flex items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors"
				on:click={() => showAdditionalOptions = !showAdditionalOptions}
			>
				<div class="flex items-center gap-2">
					<svg class="h-5 w-5 text-datadog-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M12 5v14M5 12h14" />
					</svg>
					<span class="font-medium">Additional Log Options</span>
					{#if enableFlexStarter || enableFlexStorage || enableForwarding}
						<span class="text-xs bg-datadog-blue/10 text-datadog-blue px-2 py-0.5 rounded-full">
							{[enableFlexStarter, enableFlexStorage, enableForwarding].filter(Boolean).length} selected
						</span>
					{/if}
				</div>
				<svg 
					class="h-4 w-4 text-muted-foreground transition-transform {showAdditionalOptions ? 'rotate-180' : ''}" 
					viewBox="0 0 24 24" 
					fill="none" 
					stroke="currentColor" 
					stroke-width="2"
				>
					<path d="M6 9l6 6 6-6" />
				</svg>
			</button>
			
			{#if showAdditionalOptions}
				<div class="p-4 pt-0 space-y-4 border-t border-border">
					<p class="text-xs text-muted-foreground">Add Flex Logs for cost-effective long-term storage or forward logs to external destinations.</p>
					
					<!-- Flex Logs Starter -->
					<div class="flex items-start gap-3 p-3 rounded-lg border {enableFlexStarter ? 'border-datadog-blue bg-datadog-blue/5' : 'border-border'}">
						<input 
							type="checkbox" 
							id="flexStarter"
							bind:checked={enableFlexStarter}
							class="mt-1 h-4 w-4 rounded border-border accent-datadog-blue"
						/>
						<div class="flex-1 min-w-0">
							<label for="flexStarter" class="font-medium text-sm cursor-pointer">Flex Logs Starter</label>
							<Badge variant="outline" class="ml-2 text-xs">Per 1M events stored (6, 12 or 15 months retention), per month</Badge>
							<p class="text-xs text-muted-foreground mt-1">Cost-effective compute for querying archived logs. Adapted for users who ingest less than 1TB per day.</p>
							{#if enableFlexStarter}
								<div class="mt-2 flex items-center gap-2">
									<Input 
										type="number" 
										bind:value={flexStarterGB} 
										min="1" 
										class="w-24 font-mono text-sm"
									/>
									<span class="text-xs text-muted-foreground">GB/month</span>
									{#if flexStarterPrice > 0}
										<span class="text-xs text-datadog-blue ml-auto">{formatCurrency(flexStarterCost)}/mo</span>
									{/if}
								</div>
							{/if}
						</div>
					</div>

					<!-- Flex Logs Storage -->
					<div class="flex items-start gap-3 p-3 rounded-lg border {enableFlexStorage ? 'border-datadog-blue bg-datadog-blue/5' : 'border-border'}">
						<input 
							type="checkbox" 
							id="flexStorage"
							bind:checked={enableFlexStorage}
							class="mt-1 h-4 w-4 rounded border-border accent-datadog-blue"
						/>
						<div class="flex-1 min-w-0">
							<label for="flexStorage" class="font-medium text-sm cursor-pointer">Flex Logs Storage</label>
							<Badge variant="outline" class="ml-2 text-xs">Per 1M events stored, per month</Badge>
							<p class="text-xs text-muted-foreground mt-1">Long-term storage for compliance and historical analysis. + compute price, ask your Sales Rep.</p>
							{#if enableFlexStorage}
								<div class="mt-2 flex items-center gap-2">
									<Input 
										type="number" 
										bind:value={flexStorageGB} 
										min="1" 
										class="w-24 font-mono text-sm"
									/>
									<span class="text-xs text-muted-foreground">GB/month</span>
									{#if flexStoragePrice > 0}
										<span class="text-xs text-datadog-blue ml-auto">{formatCurrency(flexStorageCost)}/mo</span>
									{/if}
								</div>
							{/if}
						</div>
					</div>

					<!-- Log Forwarding -->
					<div class="flex items-start gap-3 p-3 rounded-lg border {enableForwarding ? 'border-datadog-orange bg-datadog-orange/5' : 'border-border'}">
						<input 
							type="checkbox" 
							id="forwarding"
							bind:checked={enableForwarding}
							class="mt-1 h-4 w-4 rounded border-border accent-datadog-orange"
						/>
						<div class="flex-1 min-w-0">
							<label for="forwarding" class="font-medium text-sm cursor-pointer">Logs Forwarding to Custom Destinations</label>
							<p class="text-xs text-muted-foreground mt-0.5">Forward logs to S3, Azure, GCS, or other destinations</p>
							{#if enableForwarding}
								<div class="mt-2 flex items-center gap-2">
									<Input 
										type="number" 
										bind:value={forwardingGB} 
										min="1" 
										class="w-24 font-mono text-sm"
									/>
									<span class="text-xs text-muted-foreground">GB/month</span>
									{#if forwardingPrice > 0}
										<span class="text-xs text-datadog-orange ml-auto">{formatCurrency(forwardingCost)}/mo</span>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Results Section -->
		<div class="rounded-xl border border-border bg-muted/30 p-5 space-y-4">
			<h3 class="font-semibold text-sm uppercase tracking-wide text-muted-foreground">Calculation Results</h3>
			
			<!-- Volume Stats -->
			<div class="grid gap-4 sm:grid-cols-3">
				<div class="rounded-lg bg-background p-4 border border-border">
					<div class="text-xs text-muted-foreground mb-1">Total Logs</div>
					<div class="font-mono text-lg font-bold">{formatNumber(Math.round(totalLogsPerMonth))}</div>
					<div class="text-xs text-muted-foreground">per month</div>
				</div>
				<div class="rounded-lg bg-background p-4 border border-border">
					<div class="text-xs text-muted-foreground mb-1">Indexed Logs</div>
					<div class="font-mono text-lg font-bold text-datadog-purple">{formatNumber(Math.round(indexedLogsCount))}</div>
					<div class="text-xs text-muted-foreground">{indexedLogsInMillions.toFixed(2)}M events</div>
				</div>
				<div class="rounded-lg bg-background p-4 border border-border">
					<div class="text-xs text-muted-foreground mb-1">Retention</div>
					<div class="font-mono text-lg font-bold">{retentionDays} days</div>
					<div class="text-xs text-muted-foreground">indexed storage</div>
				</div>
			</div>

			<!-- Cost Breakdown -->
			<div class="space-y-3">
				<h4 class="text-sm font-medium">Estimated Monthly Cost</h4>
				
				<!-- Ingestion Cost -->
				<div class="flex items-center justify-between py-2 border-b border-border">
					<div class="flex items-center gap-2">
						<div class="w-3 h-3 rounded bg-datadog-blue"></div>
						<span class="text-sm">Log Ingestion ({ingestedLogsGB} GB)</span>
					</div>
					<div class="text-right">
						<span class="font-mono font-medium">{formatCurrency(ingestionCost)}</span>
						<span class="text-xs text-muted-foreground ml-2">({ingestionCostPercent.toFixed(0)}%)</span>
					</div>
				</div>

				<!-- Indexed Cost -->
				<div class="flex items-center justify-between py-2 border-b border-border">
					<div class="flex items-center gap-2">
						<div class="w-3 h-3 rounded bg-datadog-purple"></div>
						<span class="text-sm">Indexed Logs ({indexedLogsInMillions.toFixed(2)}M × {retentionDays}d)</span>
					</div>
					<div class="text-right">
						<span class="font-mono font-medium">{formatCurrency(indexedCost)}</span>
						<span class="text-xs text-muted-foreground ml-2">({indexedCostPercent.toFixed(0)}%)</span>
					</div>
				</div>

				<!-- Additional Costs -->
				{#if enableFlexStarter}
					<div class="flex items-center justify-between py-2 border-b border-border">
						<div class="flex items-center gap-2">
							<div class="w-3 h-3 rounded bg-datadog-green"></div>
							<span class="text-sm">Flex Logs Starter ({flexStarterGB} GB)</span>
						</div>
						<div class="text-right">
							<span class="font-mono font-medium">{formatCurrency(flexStarterCost)}</span>
						</div>
					</div>
				{/if}
				
				{#if enableFlexStorage}
					<div class="flex items-center justify-between py-2 border-b border-border">
						<div class="flex items-center gap-2">
							<div class="w-3 h-3 rounded bg-datadog-green"></div>
							<span class="text-sm">Flex Logs Storage ({flexStorageGB} GB)</span>
						</div>
						<div class="text-right">
							<span class="font-mono font-medium">{formatCurrency(flexStorageCost)}</span>
						</div>
					</div>
				{/if}
				
				{#if enableForwarding}
					<div class="flex items-center justify-between py-2 border-b border-border">
						<div class="flex items-center gap-2">
							<div class="w-3 h-3 rounded bg-datadog-orange"></div>
							<span class="text-sm">Log Forwarding ({forwardingGB} GB)</span>
						</div>
						<div class="text-right">
							<span class="font-mono font-medium">{formatCurrency(forwardingCost)}</span>
						</div>
					</div>
				{/if}

				<!-- Total -->
				<div class="flex items-center justify-between pt-2">
					<span class="font-semibold">Total Monthly</span>
					<span class="font-mono text-xl font-bold text-datadog-green">{formatCurrency(totalMonthlyCost)}</span>
				</div>
				<div class="flex items-center justify-between text-muted-foreground">
					<span class="text-sm">Annual Estimate</span>
					<span class="font-mono">{formatCurrency(totalAnnualCost)}/year</span>
				</div>
			</div>

			<!-- Cost Visualization -->
			<div class="h-4 rounded-full overflow-hidden bg-muted flex">
				{#if ingestionCostPercent > 0}
					<div 
						class="bg-datadog-blue transition-all duration-300" 
						style="width: {ingestionCostPercent}%"
						title="Ingestion: {ingestionCostPercent.toFixed(0)}%"
					></div>
				{/if}
				{#if indexedCostPercent > 0}
					<div 
						class="bg-datadog-purple transition-all duration-300" 
						style="width: {indexedCostPercent}%"
						title="Indexed: {indexedCostPercent.toFixed(0)}%"
					></div>
				{/if}
				{#if additionalCostPercent > 0}
					<div 
						class="bg-datadog-green transition-all duration-300" 
						style="width: {additionalCostPercent}%"
						title="Additional: {additionalCostPercent.toFixed(0)}%"
					></div>
				{/if}
			</div>
			<div class="flex justify-center flex-wrap gap-4 text-xs">
				<div class="flex items-center gap-1.5">
					<div class="w-2.5 h-2.5 rounded bg-datadog-blue"></div>
					<span>Ingestion</span>
				</div>
				<div class="flex items-center gap-1.5">
					<div class="w-2.5 h-2.5 rounded bg-datadog-purple"></div>
					<span>Indexed</span>
				</div>
				{#if additionalCost > 0}
					<div class="flex items-center gap-1.5">
						<div class="w-2.5 h-2.5 rounded bg-datadog-green"></div>
						<span>Flex/Forwarding</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- Tips -->
		<div class="rounded-lg border border-datadog-orange/30 bg-datadog-orange/5 p-4">
			<div class="flex gap-3">
				<svg class="h-5 w-5 text-datadog-orange flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="12" cy="12" r="10" />
					<line x1="12" y1="16" x2="12" y2="12" />
					<line x1="12" y1="8" x2="12.01" y2="8" />
				</svg>
				<div class="text-sm">
					<p class="font-medium text-datadog-orange mb-1">Optimization Tips</p>
					<ul class="text-muted-foreground space-y-1 list-disc list-inside">
						<li>Use exclusion filters to reduce ingested volume</li>
						<li>Index only logs needed for alerting and dashboards</li>
						<li>Consider Flex Logs for long-term, cost-effective storage</li>
						<li>Set up log pipelines to enrich and filter before indexing</li>
					</ul>
				</div>
			</div>
		</div>

		<!-- Add to Quote Button -->
		<Button 
			class="w-full gap-2 bg-datadog-purple hover:bg-datadog-purple/90"
			on:click={addToQuote}
			disabled={!ingestionProduct || !indexedProduct}
		>
			<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M12 5v14M5 12h14" />
			</svg>
			Add to Quote
		</Button>

		{#if !ingestionProduct || !indexedProduct}
			<p class="text-xs text-center text-muted-foreground">
				Some log products not found. Make sure pricing data is synced.
			</p>
		{/if}
	</CardContent>
</Card>

