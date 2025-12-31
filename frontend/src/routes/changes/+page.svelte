<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchChanges, fetchChangesSummary, type PriceChange, type ChangesSummary } from '$lib/api';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	let changes: PriceChange[] = [];
	let summary: ChangesSummary | null = null;
	let loading = true;
	let error: string | null = null;
	let selectedType: string | null = null;

	const typeLabels: Record<string, string> = {
		'price_change': 'Price Change',
		'product_added': 'New Product',
		'product_removed': 'Product Removed',
		'allotment_change': 'Allotment Change',
		'allotment_added': 'New Allotment',
		'allotment_removed': 'Allotment Removed'
	};

	const typeColors: Record<string, string> = {
		'price_change': 'bg-amber-500/10 text-amber-600 border-amber-500/30',
		'product_added': 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30',
		'product_removed': 'bg-red-500/10 text-red-600 border-red-500/30',
		'allotment_change': 'bg-blue-500/10 text-blue-600 border-blue-500/30',
		'allotment_added': 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30',
		'allotment_removed': 'bg-red-500/10 text-red-600 border-red-500/30'
	};

	const typeIcons: Record<string, string> = {
		'price_change': '💰',
		'product_added': '➕',
		'product_removed': '➖',
		'allotment_change': '🔄',
		'allotment_added': '➕',
		'allotment_removed': '➖'
	};

	function formatDate(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatRelativeTime(timestamp: string): string {
		const date = new Date(timestamp);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;
		return formatDate(timestamp);
	}

	function getFieldLabel(field: string): string {
		const labels: Record<string, string> = {
			'billed_annually': 'Annual',
			'billed_month_to_month': 'Monthly',
			'on_demand': 'On-Demand',
			'quantity_per_parent': 'Quantity',
			'monthly_on_demand': 'Monthly On-Demand',
			'hourly_on_demand': 'Hourly On-Demand'
		};
		return labels[field] || field;
	}

	$: filteredChanges = selectedType 
		? changes.filter(c => c.type === selectedType)
		: changes;

	onMount(async () => {
		try {
			[changes, summary] = await Promise.all([
				fetchChanges(200),
				fetchChangesSummary()
			]);
		} catch (e) {
			error = 'Failed to load changes. The backend might not be running.';
			console.error(e);
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Datadog Price Changes & History - PriceHound</title>
	<meta name="description" content="Track Datadog pricing changes and allotment updates. View historical price modifications across all regions and products." />
	<meta property="og:title" content="Datadog Price Changes - PriceHound" />
	<meta property="og:description" content="Track Datadog pricing changes and allotment updates across all regions." />
</svelte:head>

<div class="space-y-6">
	<!-- Header -->
	<div>
		<h1 class="text-3xl font-bold tracking-tight mb-2">Price & Allotment Changes</h1>
		<p class="text-muted-foreground">
			Track changes to Datadog pricing and allotments detected during automatic syncs.
		</p>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<svg class="h-8 w-8 animate-spin text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M21 12a9 9 0 11-6.219-8.56" />
			</svg>
		</div>
	{:else if error}
		<Card>
			<CardContent class="py-12 text-center">
				<p class="text-muted-foreground">{error}</p>
			</CardContent>
		</Card>
	{:else if changes.length === 0}
		<Card>
			<CardContent class="py-12 text-center">
				<div class="mb-4 text-4xl">📊</div>
				<h3 class="text-lg font-semibold mb-2">No changes detected yet</h3>
				<p class="text-muted-foreground">
					Changes will appear here when Datadog updates their pricing or allotments.
					The app automatically checks for changes every hour.
				</p>
			</CardContent>
		</Card>
	{:else}
		<!-- Summary Cards -->
		{#if summary}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
				<Card class="cursor-pointer hover:border-foreground/30 transition-colors {selectedType === null ? 'border-foreground/50' : ''}" on:click={() => selectedType = null}>
					<CardContent class="pt-4">
						<div class="text-2xl font-bold">{summary.total_pricing_changes + summary.total_allotment_changes}</div>
						<div class="text-xs text-muted-foreground">Total Changes</div>
					</CardContent>
				</Card>
				<Card class="cursor-pointer hover:border-foreground/30 transition-colors {selectedType === 'price_change' ? 'border-amber-500' : ''}" on:click={() => selectedType = selectedType === 'price_change' ? null : 'price_change'}>
					<CardContent class="pt-4">
						<div class="text-2xl font-bold text-amber-600">{summary.changes_by_type['price_change'] || 0}</div>
						<div class="text-xs text-muted-foreground">Price Changes</div>
					</CardContent>
				</Card>
				<Card class="cursor-pointer hover:border-foreground/30 transition-colors {selectedType === 'product_added' ? 'border-emerald-500' : ''}" on:click={() => selectedType = selectedType === 'product_added' ? null : 'product_added'}>
					<CardContent class="pt-4">
						<div class="text-2xl font-bold text-emerald-600">{summary.changes_by_type['product_added'] || 0}</div>
						<div class="text-xs text-muted-foreground">New Products</div>
					</CardContent>
				</Card>
				<Card class="cursor-pointer hover:border-foreground/30 transition-colors {selectedType === 'allotment_change' ? 'border-blue-500' : ''}" on:click={() => selectedType = selectedType === 'allotment_change' ? null : 'allotment_change'}>
					<CardContent class="pt-4">
						<div class="text-2xl font-bold text-blue-600">{summary.changes_by_type['allotment_change'] || 0}</div>
						<div class="text-xs text-muted-foreground">Allotment Changes</div>
					</CardContent>
				</Card>
			</div>
		{/if}

		<!-- Changes List -->
		<Card>
			<CardHeader>
				<CardTitle class="flex items-center gap-2">
					Recent Changes
					{#if selectedType}
						<Badge variant="outline" class="ml-2">
							Filtered: {typeLabels[selectedType]}
							<button class="ml-1 hover:text-foreground" on:click|stopPropagation={() => selectedType = null}>×</button>
						</Badge>
					{/if}
				</CardTitle>
				<CardDescription>
					{filteredChanges.length} change{filteredChanges.length !== 1 ? 's' : ''} recorded
				</CardDescription>
			</CardHeader>
			<CardContent>
				<div class="space-y-3">
					{#each filteredChanges as change}
						<div class="flex items-start gap-4 p-4 rounded-lg border border-border bg-card hover:bg-muted/30 transition-colors">
							<!-- Icon -->
							<div class="text-2xl shrink-0">
								{typeIcons[change.type] || '📋'}
							</div>
							
							<!-- Content -->
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1 flex-wrap">
									<Badge variant="outline" class="{typeColors[change.type]} border">
										{typeLabels[change.type] || change.type}
									</Badge>
									{#if change.region}
										<Badge variant="secondary" class="text-xs">
											{change.region.toUpperCase()}
										</Badge>
									{/if}
									{#if change.category}
										<Badge variant="secondary" class="text-xs">
											{change.category}
										</Badge>
									{/if}
								</div>
								
								<div class="font-medium">
									{#if change.product}
										{change.product}
									{:else if change.parent_product && change.allotted_product}
										{change.parent_product} → {change.allotted_product}
									{/if}
								</div>
								
								{#if change.type === 'price_change' && change.field}
									<div class="text-sm text-muted-foreground mt-1">
										<span class="font-medium">{getFieldLabel(change.field)}:</span>
										<span class="line-through text-red-500/70 mx-1">{change.old_value || 'N/A'}</span>
										<span class="mx-1">→</span>
										<span class="text-emerald-600 font-medium">{change.new_value || 'N/A'}</span>
									</div>
								{:else if change.type === 'allotment_change' && change.field}
									<div class="text-sm text-muted-foreground mt-1">
										<span class="font-medium">{getFieldLabel(change.field)}:</span>
										<span class="line-through text-red-500/70 mx-1">{change.old_value}</span>
										<span class="mx-1">→</span>
										<span class="text-emerald-600 font-medium">{change.new_value}</span>
									</div>
								{:else if change.data}
									<div class="text-sm text-muted-foreground mt-1">
										{#if change.data.billed_annually}
											Annual: {change.data.billed_annually}
										{/if}
										{#if change.data.billed_month_to_month}
											{#if change.data.billed_annually}, {/if}Monthly: {change.data.billed_month_to_month}
										{/if}
									</div>
								{/if}
							</div>
							
							<!-- Timestamp -->
							<div class="text-xs text-muted-foreground shrink-0 text-right">
								<div>{formatRelativeTime(change.timestamp)}</div>
								<div class="opacity-70">{formatDate(change.timestamp).split(',')[0]}</div>
							</div>
						</div>
					{/each}
				</div>
			</CardContent>
		</Card>
	{/if}
</div>

