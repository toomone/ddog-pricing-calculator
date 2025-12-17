import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	}).format(value);
}

export function parsePrice(priceStr: string | null | undefined): number {
	if (!priceStr || priceStr === '-' || priceStr === '') return 0;
	const cleaned = priceStr.replace(/[^\d.]/g, '');
	return parseFloat(cleaned) || 0;
}

