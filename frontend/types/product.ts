export interface ProductMoney {
  currency: string;
  minorUnits: number;
}

/** Frontend projection of a product/listing result from Product Intelligence. */
export interface Product {
  productId: string;
  variantId?: string;
  listingId?: string;
  observationId?: string;
  name: string;
  brand?: string;
  pack?: string;
  platform: string;
  price?: ProductMoney;
  availability?: string;
  imageUrl?: string;
  evidenceState?: "registered_governed_observation";
  observedAt?: string;
  parserVersion?: string;
  variantAttributes?: readonly { name: string; value: string; role: string; assertionStatus: string }[];
  retailerProductId?: string;
  retailerProductUrl?: string;
  normalizationVersion?: string;
  sourceReference?: string;
  rawArtifactId?: string;
  rawContentDigest?: string;
  evidenceReferences?: readonly { sourceType: string; sourceId: string }[];
  identityAttributes?: readonly { name: string; value: string; role: string; assertionStatus: string }[];
}
